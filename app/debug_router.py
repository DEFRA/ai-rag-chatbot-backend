from fastapi import APIRouter

from app.core.rag.vector_store import vector_store_grants

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/vector-store-docs")
def list_vector_store_docs():
    """Return a list of all documents in the vector store (for debugging)."""
    if vector_store_grants is None:
        return {"error": "Vector store not initialized."}
    # Chroma's get() returns a dict with 'documents' and 'metadatas'
    results = vector_store_grants.get()
    docs = results.get("documents", [])
    metadatas = results.get("metadatas", [])
    # Return a list of dicts with content and metadata
    return [{"content": doc, "metadata": meta} for doc, meta in zip(docs, metadatas)]
