import os

from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings

from app.config import config as configs

# --- Configuration ---
# Define the path where the vector store will be persisted
GRANTS_VECTORSTORE_PATH = "./chroma_db_grants"
COLLECTION_NAME = "rag-chroma"
embedding_model = None

try:
    # Define model used for embedding
    embedding_model = AzureOpenAIEmbeddings(
        model="text-embedding-3-small",
        azure_deployment="text-embedding-3-small",
        azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
        api_key=configs.AZURE_OPENAI_API_KEY,
        api_version=configs.AZURE_API_VERSION,
    )
    print("Embedding model initialized successfully.")
except Exception as e:
    print(
        f"CRITICAL: Error initializing embedding model: {e}. Vector store operations will likely fail."
    )


# --- Initialize/Load Vector Store ---
vector_store_grants = None
retriever = None


# --- Initialize Retriever ---
if embedding_model:  # Proceed only if the embedding model was initialized
    try:
        # Initialising a Chroma object for vector_store_grants.
        # If GRANTS_VECTORSTORE_PATH exists, Chroma will attempt to load it.
        # If not, it's an in-memory ready instance for ingest_markdown_docs.py to populate and persist.
        print(
            f"Initializing Chroma for 'vector_store_grants' with path: {GRANTS_VECTORSTORE_PATH} and collection: '{COLLECTION_NAME}'"
        )

        vector_store_grants = Chroma(
            persist_directory=GRANTS_VECTORSTORE_PATH,
            embedding_function=embedding_model,
            collection_name=COLLECTION_NAME,
        )
        print("'vector_store_grants' (Chroma instance) initialized.")

        # Initialize retriever only if the persistent store exists AND has documents.
        # Check if the collection actually has documents before creating a retriever
        if os.path.exists(GRANTS_VECTORSTORE_PATH) and os.path.isdir(
            GRANTS_VECTORSTORE_PATH
        ):
            # The vector_store_grants instance above would have loaded data if the path existed.
            if (
                vector_store_grants._collection.count() > 0
            ):  # Check if the collection has any documents
                retriever = vector_store_grants.as_retriever()
                print(
                    f"Retriever initialized from existing vector store with {vector_store_grants._collection.count()} documents."
                )
            else:
                # This means the directory exists but the specific collection is empty or not found as expected.
                print(
                    f"Vector store path {GRANTS_VECTORSTORE_PATH} exists but collection '{COLLECTION_NAME}' is empty. Retriever not initialized. Run ingestion."
                )
        else:
            # This case will be hit by ingest_markdown_docs.py on its first run.
            # vector_store_grants is a Chroma instance, but retriever remains None.
            print(
                f"Vector store path {GRANTS_VECTORSTORE_PATH} does not exist. Retriever not initialized. Ingestion script should create it."
            )

    except Exception as e:
        print(f"Error during Chroma/Retriever initialization: {e}")
        vector_store_grants = None  # Ensure reset on error
        retriever = None
else:
    print(
        "Embedding model not initialized. Vector store and retriever will be unavailable."
    )


# Final status print for clarity during startup
if vector_store_grants is None:
    # This should now only happen if embedding_model failed OR the Chroma() call itself failed.
    print(
        "`vector_store_grants` is None. Ingestion script might not work as expected if it relies on this instance being pre-loaded."
    )
if retriever is None:
    print(
        "`retriever` is None. Agentic graph queries to the vector store will likely fail or use no context."
    )
