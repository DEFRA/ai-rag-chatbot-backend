import json
from typing import Literal

from langchain import hub
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from app.clients.azure_openai_config import azure_gpt4o
from app.core.agents.agent_state import AgentState
from app.core.agents.agent_tools import tools
from app.core.rag.vector_store import retriever


def debug_tools_condition(state):
    user_query = state["messages"][0].content.lower()
    gov_keywords = [
        "universal credit",
        "benefits",
        "housing",
        "landlord",
        "rented",
        "government",
        "ai ethics",
        "artificial intelligence",
        "government guidance",
        "fairness",
        "accountability",
        "transparency",
    ]
    result = tools_condition(state)
    print(f"TOOL CONDITION OUTPUT FROM LLM: {result}")
    if any(keyword in user_query for keyword in gov_keywords):
        print(
            "\U0001f50d Detected gov-related keyword and no retrieval yet — forcing retriever tool."
        )
        return "tools"
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
        content=(
            "You are a helpful assistant. Use tools when relevant. "
            "You MUST use the `gov_knowledge_base` tool for any question about UK government information "
            "regarding Universal Credit, housing, benefit payments, or AI ethics and safety. "
            "Do NOT attempt to answer on your own for these topics — use the tool."
        ),
        name="system",
    )

    model = azure_gpt4o(temperature=0, streaming=False)
    model = model.bind_tools(tools)

    response = model.invoke([system_msg] + messages)

    tool_calls = response.additional_kwargs.get("tool_calls", [])

    if tool_calls:
        print(f"⚙️ Tool calls detected: {tool_calls}")
        tool_messages = []
        tool_response = None

        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            tool_args = json.loads(tool_call["function"]["arguments"])
            tool_call_id = tool_call["id"]

            if tool_name == "gov_knowledge_base":
                tool_response = retriever.invoke(tool_args["query"])
                tool_messages.append(
                    ToolMessage(
                        tool_call_id=tool_call_id, content="Retrieved documents."
                    )
                )

        return {
            "messages": [response] + tool_messages,
            "docs": tool_response,
            "retrieval_attempted": True,
            "should_generate": True,
        }

    return {"messages": [response]}


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
    question = state["messages"][0].content
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
    return {"messages": [full_response]}


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

# Compile graph
graph = workflow.compile()

# Save mermaid diagram
image_data = graph.get_graph().draw_mermaid_png()
with open("agentic_graph.png", "wb") as f:
    f.write(image_data)


# # create image of nodes
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
