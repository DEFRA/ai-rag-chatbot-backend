from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings

from app.config import config as configs

from .data_ingest import doc_splits

# Define model used for embedding
embedding_model = AzureOpenAIEmbeddings(
    model="text-embedding-3-small",
    azure_deployment="text-embedding-3-small",
    azure_endpoint=configs.AZURE_OPENAI_ENDPOINT,
    api_key=configs.AZURE_OPENAI_API_KEY,
    api_version=configs.AZURE_API_VERSION,
)

# Add data to vectorDB
vectorstore = Chroma.from_documents(
    documents=doc_splits,
    collection_name="rag-chroma",
    embedding=embedding_model,
)
retriever = vectorstore.as_retriever()

print("Vector store and retriever initialized.")
