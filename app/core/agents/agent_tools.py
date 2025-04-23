from langchain.tools.retriever import create_retriever_tool

from app.core.rag.vector_store import retriever

# retriever tool
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="web_retriever",
    description="Search and return information about Lilian Weng blog posts on LLM agents, prompt engineering, and adversarial attacks on LLMs.",
)
tools = [retriever_tool]

print("Retriever tool created.")
