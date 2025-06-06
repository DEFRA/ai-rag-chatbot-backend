from langchain_chroma import Chroma

from app.core.rag.vector_store import embedding_model

# Path to vector store
COLLECTION_NAME = "rag-chroma"

# Load the vector store
vector_store = Chroma(
    embedding_function=embedding_model, collection_name=COLLECTION_NAME
)

# Get all documents in the vector store
all_docs = vector_store.get(include=["metadatas", "documents"])
print(f"Total documents in vector store: {len(all_docs['documents'])}")


def show_documents_in_vector_store(all_docs):
    """
    Print all documents in the vector store.
    """
    for i, doc in enumerate(all_docs["documents"]):
        metadata = all_docs["metadatas"][i]
        print(f"Document {i + 1}:")
        print(f"Content: {doc[:100]}")  # Print first 100 characters of the document
        print(f"Metadata: {metadata}")
        print("-" * 40)


show_documents_in_vector_store(all_docs)
