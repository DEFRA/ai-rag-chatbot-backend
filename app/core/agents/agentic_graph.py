import json
from typing import Literal

from langchain import hub
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.clients.azure_openai_config import azure_gpt4, azure_gpt4o
from app.core.agents.agent_state import AgentState
from app.core.agents.agent_tools import retriever_tool, tools


### Edges
def check_document_relevance(state) -> Literal["generate", "rewrite"]:
    """
    Determines whether the retrieved documents are relevant to the question.
    """
    print("---CHECK RELEVANCE---")

    model = azure_gpt4(
        temperature=0, streaming=False
    )  # Disable streaming for simpler invoke/parse

    # Modify prompt to explicitly ask for JSON output
    prompt = PromptTemplate(
        template="""You are a grader assessing relevance of a retrieved document to a user question.
        Here is the retrieved document:
        {context}

        Here is the user question:
        {question}

        If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
        Respond ONLY with a valid JSON object containing a single key "binary_score" with the value "yes" or "no".
        Example: {{"binary_score": "yes"}}

        JSON Response:""",
        input_variables=["context", "question"],
    )

    # Simpler chain for raw output
    chain = prompt | model | StrOutputParser()

    messages = state["messages"]
    last_message = messages[-1]
    question = messages[0].content
    docs = (
        last_message.content
    )  # Assuming docs is already a string or formatted correctly here

    # Invoke the chain to get the raw string output
    raw_json_output = chain.invoke({"question": question, "context": docs})
    print(f"DEBUG: Raw output from grading model: {raw_json_output}")

    score = "no"  # Default score
    try:
        # Attempt to parse the JSON string
        parsed_output = json.loads(raw_json_output.strip())
        if "binary_score" in parsed_output and parsed_output["binary_score"] in [
            "yes",
            "no",
        ]:
            score = parsed_output["binary_score"]
        else:
            print("WARN: JSON output missing 'binary_score' or invalid value.")
    except json.JSONDecodeError:
        print(f"ERROR: Failed to decode JSON from model output: {raw_json_output}")
    except Exception as e:
        print(f"ERROR: Unexpected error parsing JSON: {e}")

    if score == "yes":
        print("---DECISION: DOCS RELEVANT---")
        return "generate"

    print(f"---DECISION: DOCS NOT RELEVANT (Score: {score})---")
    return "rewrite"


### Nodes
def agent(state):
    """
    Invokes the agent model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply end.

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with the agent response appended to messages
    """
    print("---CALL AGENT---")
    messages = state["messages"]
    model = azure_gpt4(temperature=0, streaming=True)
    model = model.bind_tools(tools)
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


def rewrite(state):
    """
    Transform the query to produce a better question.

    Args:
        state (messages): The current state

    Returns:
        dict: The updated state with re-phrased question
    """

    print("---TRANSFORM QUERY---")
    messages = state["messages"]
    question = messages[0].content

    msg = [
        HumanMessage(
            content=f""" \n
    Look at the input and try to reason about the underlying semantic intent / meaning. \n
    Here is the initial question:
    \n ------- \n
    {question}
    \n ------- \n
    Formulate an improved question: """,
        )
    ]

    # Grader
    model = azure_gpt4(temperature=0, streaming=True)
    response = model.invoke(msg)
    return {"messages": [response]}


def generate(state):
    """
    Generate answer

    Args:
        state (messages): The current state

    Returns:
         dict: The updated state with re-phrased question
    """
    print("---GENERATE---")
    messages = state["messages"]
    question = messages[0].content
    last_message = messages[-1]

    docs = last_message.content

    # Prompt
    prompt = hub.pull("rlm/rag-prompt")

    # LLM
    llm = azure_gpt4o(temperature=0, streaming=True)

    # Post-processing
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Chain
    rag_chain = prompt | llm | StrOutputParser()

    # Run
    response = rag_chain.invoke({"context": docs, "question": question})
    return {"messages": [response]}


print("*" * 20 + "Prompt[rlm/rag-prompt]" + "*" * 20)
prompt = hub.pull("rlm/rag-prompt").pretty_print()  # Show what the prompt looks like


# Define a new graph
workflow = StateGraph(AgentState)

# Define the nodes we will cycle between
workflow.add_node("agent", agent)  # agent
retrieve = ToolNode([retriever_tool])
workflow.add_node("retrieve", retrieve)  # retrieval
workflow.add_node("rewrite", rewrite)  # Re-writing the question
workflow.add_node(
    "generate", generate
)  # Generating a response after we know the documents are relevant
# Call agent node to decide to retrieve or not
workflow.add_edge(START, "agent")

# Decide whether to retrieve
workflow.add_conditional_edges(
    "agent",
    # Assess agent decision
    tools_condition,
    {
        # Translate the condition outputs to nodes in our graph
        "tools": "retrieve",
        END: END,
    },
)

# Edges taken after the `action` node is called.
workflow.add_conditional_edges(
    "retrieve",
    # Assess agent decision
    check_document_relevance,
)
workflow.add_edge("generate", END)
workflow.add_edge("rewrite", "agent")

# Compile
graph = workflow.compile()

# create image of nodes
# import pprint
# inputs = {
#     "messages": [
#         ("user", "What does Lilian Weng say about the types of agent memory?"),
#     ]
# }
# for output in graph.stream(inputs):
#     for key, value in output.items():
#         pprint.pprint(f"Output from node '{key}':")
#         pprint.pprint("---")
#         pprint.pprint(value, indent=2, width=80, depth=None)
#     pprint.pprint("\n---\n")
