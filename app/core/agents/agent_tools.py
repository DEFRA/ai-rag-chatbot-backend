from langchain.tools.retriever import create_retriever_tool

from app.core.rag.vector_store import retriever


# Build description dynamically from resource metadata
def build_tool_description():
    """Builds a general description for the farming grants knowledge base tool."""
    description = (
        "Use this tool to search a specialized knowledge base for information about UK farming grants, "
        "agricultural funding, rural support schemes, and related guidance from GOV.UK. "
        "This tool is essential for answering questions about eligibility, application processes, "
        "types of grants available, and other details pertaining to financial support for the farming sector."
    )
    return description  # noqa: RET504


# Create retriever tool with rich description
retriever_tool = create_retriever_tool(
    retriever=retriever,
    name="gov_knowledge_base",
    description=build_tool_description(),
)

tools = [retriever_tool]

print("Retriever tool for GOV.UK farming grants knowledge base created.")
