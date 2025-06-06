from langchain_chroma import Chroma
from langchain_openai import AzureOpenAIEmbeddings

from app.config import config as configs

# --- Configuration ---
# Define the collection name for the in-memory vector store
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
        # Initialising a Chroma object for vector_store_grants in-memory (no persistence).
        print(
            f"Initializing in-memory Chroma for 'vector_store_grants' with collection: '{COLLECTION_NAME}'"
        )

        vector_store_grants = Chroma(
            embedding_function=embedding_model,
            collection_name=COLLECTION_NAME,
        )
        print("'vector_store_grants' (Chroma instance, in-memory) initialized.")

        # Always initialize retriever for in-memory store (will be empty on startup)
        retriever = vector_store_grants.as_retriever()
        print("Retriever initialized for in-memory vector store.")

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
    print(
        "`vector_store_grants` is None. Ingestion script might not work as expected if it relies on this instance being pre-loaded."
    )
if retriever is None:
    print(
        "`retriever` is None. Agentic graph queries to the vector store will likely fail or use no context."
    )
