import json
from typing import Literal

from langchain import hub
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.clients.azure_openai_config import azure_gpt4o
from app.core.agents.agent_state import AgentState
from app.core.agents.agent_tools import tools
from app.core.rag.vector_store import retriever


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


def agent(state):
    print("---CALL AGENT---")
    messages = state["messages"]
    system_msg = HumanMessage(
        content="""You are a helpful assistant.
You have access to a specialized knowledge base about UK farming grants.
You MUST use the `gov_knowledge_base` tool for any question related to farming, farming grants, agricultural funding, rural support schemes, or similar topics.
Do NOT attempt to answer on your own for these topics — always use the `gov_knowledge_base` tool to ensure accuracy based on the provided documents.
For other general queries, you can answer directly or use other tools if appropriate.

You should remember and use all information the user shares with you during the conversation, including their name, preferences, goals, and any facts or context discussed. If the user asks you to recall or summarize what has been discussed so far, look back through the conversation and answer accordingly.""",
        name="system",
    )

    model = azure_gpt4o(temperature=0, streaming=False)
    model = model.bind_tools(tools)

    response = model.invoke([system_msg] + messages)
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

    # Find the most recent user query
    question = None
    for msg in reversed(messages):
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
    # Use the most recent user message as the question instead of always the first message
    messages = state["messages"]

    # Find the most recent user query - it's generally the last HumanMessage
    question = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    # Fallback to the first message if we couldn't find a HumanMessage
    if question is None and messages:
        question = messages[0].content

    docs = state.get("docs", [])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def collect_sources(docs):
        source = set()
        for doc in docs:
            url = doc.metadata.get("url")
            title = doc.metadata.get("title", "Unknown Title")
            if url:
                source.add(f"{title}: {url}")
        return "\n".join(sorted(source)) if source else "No sources found."

    prompt = hub.pull("rlm/rag-prompt")
    llm = azure_gpt4o(temperature=0, streaming=False)
    rag_chain = prompt | llm | StrOutputParser()

    response = rag_chain.invoke({"context": format_docs(docs), "question": question})
    cited_sources = collect_sources(docs)
    full_response = f"{response}\n\nSources:\n{cited_sources}"

    # Return the new message as an AIMessage object in a list
    return {"messages": [AIMessage(content=full_response)]}


# ========== BUILD GRAPH ===========
print("****************** Prompt[rlm/rag-prompt] ******************")
hub.pull("rlm/rag-prompt").pretty_print()

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
    """
    from langchain_core.messages import HumanMessage

    # Prepare the config with thread_id for memory persistence
    config = {"configurable": {"thread_id": user_id}}

    # Get current state from memory, if any exists
    current_state = graph.get_state(config=config)

    # If no state exists, initialize with just the new query
    if not current_state or "messages" not in current_state:
        print(f"No existing state found for user {user_id}, creating fresh state")
        initial_state = {"messages": [HumanMessage(content=user_query)]}
    else:
        # Otherwise, append the new message to existing conversation history
        print(
            f"Found existing state for user {user_id} with {len(current_state.get('messages', []))} messages"
        )
        # Create a copy to avoid modifying the original
        initial_state = dict(current_state)
        # Add the new user message to existing conversation
        initial_state["messages"] = list(initial_state["messages"]) + [
            HumanMessage(content=user_query)
        ]

    # Invoke the graph - memory handling is automatic with the checkpointer
    return graph.invoke(initial_state, config)


# Save mermaid diagram
image_data = graph.get_graph().draw_mermaid_png()
with open("agentic_graph_new.png", "wb") as f:
    f.write(image_data)


# create image of nodes
# import pprint
# inputs = {
#     "messages": [
#         ("user", "What does the government say about AI and ethics, specifically on transparency?"),
#     ]
# }
# for output in graph.stream(inputs):
#     for key, value in output.items():
#         pprint.pprint(f"Output from node '{key}':")
#         pprint.pprint("---")
#         pprint.pprint(value, indent=2, width=80, depth=None)
#     pprint.pprint("\n---\n")
