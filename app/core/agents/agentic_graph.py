import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.clients.azure_openai_config import azure_gpt4o
from app.core.agents.agent_state import AgentState
from app.core.agents.agent_tools import tools
from app.core.rag.vector_store import retriever
from app.util.prompts import base_prompt


def debug_tools_condition(state):
    # Find the most recent user query
    user_query = None
    messages = state["messages"]
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content.lower()
            break
    if user_query is None and messages:
        user_query = messages[0].content.lower()

    farming_grant_keywords = [
        "farm",
        "farming",
        "grant",
        "grants",
        "agriculture",
        "agricultural",
        "rural",
        "defra",
        "funding",
        "support scheme",
    ]
    question_starters = [
        "what",
        "how",
        "which",
        "when",
        "where",
        "who",
        "does",
        "do",
        "can",
        "is",
        "are",
        "should",
        "could",
        "would",
    ]

    # Check if it's a question
    is_question = user_query.strip().endswith("?") or any(
        user_query.strip().startswith(qs + " ") for qs in question_starters
    )

    # Only trigger retrieval if BOTH a keyword and a question are present
    if is_question and any(keyword in user_query for keyword in farming_grant_keywords):
        print(
            "Detected farming grant-related keyword in a question — forcing retriever tool."
        )
        return "tools"

    # Otherwise, use the LLM's own tool condition logic
    result = tools_condition(state)
    print(f"TOOL CONDITION OUTPUT FROM LLM: {result}")
    return result


def check_document_relevance(state) -> Literal["generate", "rewrite"]:
    print("---CHECK RELEVANCE---")
    model = azure_gpt4o(temperature=0, streaming=False)
    prompt = PromptTemplate(
        template="""You are a grader assessing relevance of a retrieved document to a user question.
        Here is the retrieved document:
        {context}

        Here is the user question:
        {question}

        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
        Respond ONLY with 'yes' or 'no'.

        Response:""",
        input_variables=["context", "question"],
    )
    chain = prompt | model | StrOutputParser()

    messages = state["messages"]
    last_message = messages[-1]

    # Find the most recent user query - look through messages in reverse
    question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    # Fallback to first message if no HumanMessage found
    if question is None and messages:
        question = messages[0].content

    docs = last_message.content

    raw_output = chain.invoke({"question": question, "context": docs})
    print(f"DEBUG: Raw output from grading model: {raw_output}")

    cleaned_output = raw_output.strip().lower()
    print(f"*********Cleaned String to parse: {cleaned_output}")

    if "yes" in cleaned_output:
        print("---DECISION: DOCS RELEVANT---")
        return "generate"

    print(f"---DECISION: DOCS NOT RELEVANT (Score: {cleaned_output})---")
    return "rewrite"


# Utility: Limit conversation history for LLM context window
MAX_CONTEXT_MESSAGES = 10  # Adjust as needed for your LLM's context window

# Summarize older messages if conversation is too long


def get_recent_messages(messages, max_messages=MAX_CONTEXT_MESSAGES):
    """
    Returns the most recent max_messages from the conversation history.
    If there are more messages, older ones are summarized into a single message.
    """
    if len(messages) <= max_messages:
        return messages
    # Summarize older messages
    older_messages = messages[:-max_messages]
    recent_messages = messages[-max_messages:]

    # Prepare a summary prompt
    summary_prompt = PromptTemplate(
        template="""
You are an assistant helping to summarize a conversation for context recall. Summarize the following conversation history in a concise way, preserving key facts, user preferences, and important context. Do not invent information.

Conversation history:
{history}

Summary:""",
        input_variables=["history"],
    )
    # Format the older messages as a string
    history_text = "\n".join(f"{msg.type}: {msg.content}" for msg in older_messages)
    model = azure_gpt4o(temperature=0, streaming=False)
    chain = summary_prompt | model | StrOutputParser()
    summary = chain.invoke({"history": history_text})
    # Return a SystemMessage with the summary, plus the recent messages
    summary_message = SystemMessage(content=f"Conversation summary: {summary}")
    return [summary_message] + recent_messages


def agent(state):
    print("---CALL AGENT---")
    messages = state["messages"]
    system_msg = SystemMessage(
        content="""
You are an expert assistant helping users ONLY with questions about UK farming grants, agricultural funding, and related topics. You MUST NOT answer questions outside these topics. If the user's question is not related to these topics, politely respond: 'Sorry, I can only assist with farming grants, funding, and related topics.'

You have access to a specialized knowledge base about UK farming grants. You MUST use the `gov_knowledge_base` tool for any question related to farming, farming grants, agricultural funding, rural support schemes, or similar topics. Do NOT attempt to answer on your own for these topics — always use the `gov_knowledge_base` tool to ensure accuracy based on the provided documents.

You should remember and use all information the user shares with you during the conversation, including their name, preferences, goals, and any facts or context discussed. If the user asks you to recall or summarize what has been discussed so far, look back through the conversation and answer accordingly.
""",
        name="system",
    )

    # Use only the most recent messages for LLM context
    recent_messages = get_recent_messages(messages)

    model = azure_gpt4o(temperature=0, streaming=False)
    model = model.bind_tools(tools)

    response = model.invoke([system_msg] + recent_messages)
    tool_calls = response.additional_kwargs.get("tool_calls", [])

    # Prepare the list of new messages to add
    new_messages_to_add = [response]  # Start with the LLM response

    tool_response_docs = (
        None  # Use a different name to avoid confusion with state['docs']
    )
    retrieval_attempted_in_node = False
    should_generate_in_node = False

    if tool_calls:
        print(f"Tool calls detected: {tool_calls}")
        tool_messages = []
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            tool_call_id = tool_call["id"]

            if tool_name == "gov_knowledge_base":
                # Store the retrieved docs temporarily
                tool_response_docs = retriever.invoke(tool_args["query"])
                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tool_call_id,
                        # Content can be a summary or confirmation
                        content=f"Retrieved {len(tool_response_docs)} documents related to '{tool_args['query']}'.",
                    )
                )
                retrieval_attempted_in_node = True
                should_generate_in_node = (
                    True  # Assuming tool use means we should generate next
                )

        # Add the tool messages to the list of new messages
        new_messages_to_add.extend(tool_messages)

    # Return only the new messages and other state updates
    return_dict = {"messages": new_messages_to_add}
    if tool_response_docs is not None:
        return_dict["docs"] = tool_response_docs
    if retrieval_attempted_in_node:
        return_dict["retrieval_attempted"] = True  # Or update based on logic
    if should_generate_in_node:
        return_dict["should_generate"] = True  # Or update based on logic

    return return_dict


def retrieve_and_store(state):
    print("---RETRIEVE AND STORE---")
    query = state["messages"][-1].content
    documents = retriever.invoke(query)

    retrieval_message = HumanMessage(content="Documents retrieved.")
    return {
        "messages": [retrieval_message],
        "docs": documents,
        "retrieval_attempted": True,
    }


def rewrite(state):
    print("---TRANSFORM QUERY---")
    messages = state["messages"]
    # Use only the most recent messages for LLM context
    recent_messages = get_recent_messages(messages)

    # Find the most recent user query
    question = None
    for msg in reversed(recent_messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    # Fallback to the first message if no human message found
    if question is None and messages:
        question = messages[0].content

    msg = [
        HumanMessage(
            content=f"""
    Look at the input and try to reason about the underlying semantic intent / meaning.
    Here is the initial question:
    \n ------- \n
    {question}
    \n ------- \n
    Formulate an improved question: """,
        )
    ]

    model = azure_gpt4o(temperature=0, streaming=False)
    response = model.invoke(msg)
    return {"messages": [response]}


def generate(state):
    print("---GENERATE---")
    messages = state["messages"]
    # Use only the most recent messages for LLM context
    recent_messages = get_recent_messages(messages)

    # Find the most recent user query - it's generally the last HumanMessage
    question = None
    for msg in reversed(recent_messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    # Fallback to the first message if we couldn't find a HumanMessage
    if question is None and messages:
        question = messages[0].content

    docs = state.get("docs", [])

    # If no relevant docs, refuse to answer
    if not docs or len(docs) == 0:
        return {
            "messages": [
                AIMessage(
                    content="Sorry, I can only assist with farming grants, funding, and related topics. If you have a question about those, please ask!"
                )
            ]
        }

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def collect_sources(docs):
        source = set()
        for doc in docs:
            url = doc.metadata.get("url")
            title = doc.metadata.get("title", "Unknown Title")
            if url:
                source.add(f"{title}: {url}")
        return "\n".join(sorted(source)) if source else ""

    llm = azure_gpt4o(temperature=0, streaming=False)
    rag_chain = base_prompt | llm | StrOutputParser()

    response = rag_chain.invoke({"context": format_docs(docs), "question": question})
    cited_sources = collect_sources(docs)
    # Only show sources if there is a substantive answer
    if response.strip().lower().startswith("sorry") or not response.strip():
        full_response = response.strip()
    else:
        full_response = (
            f"{response}\n\nSources:\n{cited_sources}" if cited_sources else response
        )

    # Return the new message as an AIMessage object in a list
    return {"messages": [AIMessage(content=full_response)]}


# ========== BUILD GRAPH ===========
print("****************** Prompt[rlm/rag-prompt] ******************")
base_prompt.pretty_print()

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent)
workflow.add_node("retrieve", retrieve_and_store)
workflow.add_node("rewrite", rewrite)
workflow.add_node("generate", generate)

workflow.add_edge(START, "agent")

workflow.add_conditional_edges(
    "agent",
    lambda state: "generate"
    if state.get("should_generate")
    else debug_tools_condition(state),
    {"generate": "generate", "tools": "retrieve", END: END},
)

workflow.add_conditional_edges(
    "retrieve", check_document_relevance, {"generate": "generate", "rewrite": "rewrite"}
)

workflow.add_edge("generate", END)
workflow.add_edge("rewrite", "agent")

# --- MemorySaver integration ---
# Initialize MemorySaver (default: in-memory storage)
memory = MemorySaver()

# Compile graph with memory checkpointer
graph = workflow.compile(checkpointer=memory)


def run_graph_with_memory(user_id: str, user_query: str):
    """
    Runs the graph with memory persistence for the given user.

    The checkpointer (MemorySaver) automatically handles loading prior state
    and saving the new state after execution.
    Now includes robust error handling to preserve conversation state even on error.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    config = {"configurable": {"thread_id": user_id}}
    try:
        current_state = graph.get_state(config=config)
        if not current_state or "messages" not in current_state:
            print(f"No existing state found for user {user_id}, creating fresh state")
            initial_state = {"messages": [HumanMessage(content=user_query)]}
        else:
            print(
                f"Found existing state for user {user_id} with {len(current_state.get('messages', []))} messages"
            )
            initial_state = dict(current_state)
            # Only add the new message if it's not a duplicate of the last message
            if (
                not initial_state["messages"]
                or initial_state["messages"][-1].content != user_query
            ):
                initial_state["messages"] = list(initial_state["messages"]) + [
                    HumanMessage(content=user_query)
                ]
        return graph.invoke(initial_state, config)
    except Exception as e:
        # On error, append a system message to the conversation
        print(f"Error in run_graph_with_memory: {e}")
        error_message = SystemMessage(
            content=f"An error occurred: {str(e)}. Your previous conversation is saved. Please try again."
        )
        # Try to append error message to the last known state
        try:
            if "initial_state" in locals():
                initial_state["messages"].append(error_message)
            elif (
                "current_state" in locals()
                and current_state
                and "messages" in current_state
            ):
                current_state["messages"].append(error_message)
            else:
                # If all else fails, create a minimal state
                fallback_state = {
                    "messages": [HumanMessage(content=user_query), error_message]
                }
        except Exception as persist_error:
            print(f"Failed to update error state: {persist_error}")
        # Optionally, re-raise or return a fallback response
        raise
