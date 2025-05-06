import os

from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings

from app.config import config as configs

# Define model used for embedding
embedding_model = AzureOpenAIEmbeddings(
    model="text-embedding-3-small",
    azure_deployment="text-embedding-3-small",
    azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
    api_key=configs.AZURE_OPENAI_API_KEY,
    api_version=configs.AZURE_API_VERSION,
)

# --- Configuration ---
# Define the path where the vector store will be persisted
GRANTS_VECTORSTORE_PATH = "./chroma_db_grants"

# --- Initialize/Load Vector Store ---
vector_store_grants = None
if os.path.exists(GRANTS_VECTORSTORE_PATH):
    print(f"Loading existing vector store from {GRANTS_VECTORSTORE_PATH}...")
    vector_store_grants = Chroma(
        persist_directory=GRANTS_VECTORSTORE_PATH,
        embedding_function=embedding_model,
        collection_name="rag-chroma",  # Ensure collection name matches ingestion
    )
else:
    print(
        f"Vector store not found at {GRANTS_VECTORSTORE_PATH}. Please run the ingestion script first."
    )


# --- Initialize Retriever ---
# Ensure retriever is initialized only if vector_store_grants is loaded
if vector_store_grants:
    retriever_grants = vector_store_grants.as_retriever()  # Renamed for clarity
    print("Grants vector store and retriever initialized.")
else:
    retriever_grants = None  # Or handle appropriately
    print("Grants vector store not loaded, retriever not initialized.")
