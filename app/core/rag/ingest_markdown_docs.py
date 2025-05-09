import json
import time

from langchain.schema.document import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import the pre-configured vector store and its path from vector_store.py
from app.core.rag.vector_store import GRANTS_VECTORSTORE_PATH, vector_store_grants

# --- Configuration ---
PROCESSED_JSON_PATH = "farming_grants_processed.json"  # Path to the JSON file from data_ingest_via_search_apiv2.py
CHUNK_SIZE = 1000  # Adjust based on your LLM's context window and typical grant length
CHUNK_OVERLAP = 200  # Adjust overlap based on chunk size
# Ensure OPENAI_API_KEY is set as an environment variable


# --- Main Logic ---
def load_processed_data(json_path):
    """Loads the processed data (markdown + metadata) from the JSON file."""
    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded {len(data)} documents from {json_path}")
        return data
    except FileNotFoundError:
        print(f"Error: Processed data file not found at {json_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {json_path}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred loading {json_path}: {e}")
        return []


def create_langchain_documents(processed_data):
    """Converts processed data dictionaries into LangChain Document objects."""
    documents = []
    for item in processed_data:
        if "markdown_content" in item and "metadata" in item:
            # Ensure metadata values are strings or basic types suitable for vector stores
            metadata = {
                k: str(v) if v is not None else "" for k, v in item["metadata"].items()
            }
            doc = Document(page_content=item["markdown_content"], metadata=metadata)
            documents.append(doc)
        else:
            print(
                f"Skipping item due to missing 'markdown_content' or 'metadata': {item.get('metadata', {}).get('url', 'N/A')}"
            )
    print(f"Created {len(documents)} LangChain Document objects.")
    return documents


def split_documents(documents):
    """Splits LangChain Documents into smaller chunks."""
    if not documents:
        return []
    print(
        f"Splitting {len(documents)} documents into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})..."
    )
    # Using RecursiveCharacterTextSplitter suitable for Markdown
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        # separators=["\n\n", "\n", " ", ""] # Default separators often work well
    )
    doc_splits = text_splitter.split_documents(documents)
    print(f"Created {len(doc_splits)} document chunks.")
    return doc_splits


def ingest_to_vectorstore(doc_splits, batch_size=50, max_retries=3, backoff=60):
    """Adds document splits to the pre-configured grants vector store with retry logic."""
    if not doc_splits:
        print("No document splits to ingest.")
        return

    if vector_store_grants is None:
        print(
            "Error: Grants vector store is not initialized. "
            "This might be due to an issue with OpenAIEmbeddings initialization in vector_store.py "
            "(e.g., OPENAI_API_KEY not set)."
        )
        return

    print(
        f"Using pre-configured Chroma vector store for grants at {GRANTS_VECTORSTORE_PATH}."
    )

    print(f"Adding {len(doc_splits)} document chunks to the vector store...")
    try:
        for i in range(0, len(doc_splits), batch_size):
            batch = doc_splits[i : i + batch_size]
            retries = 0
            while retries <= max_retries:
                try:
                    vector_store_grants.add_documents(batch)
                    print(
                        f"Added batch {i // batch_size + 1} /{-(-len(doc_splits) // batch_size)} to vector store."
                    )
                    break  # Exit retry loop if successful
                except Exception as e:
                    if "429" in str(e):
                        retries += 1
                        print(
                            f"Rate limit hit. Retrying batch {i // batch_size + 1} in {backoff} seconds... (Attempt {retries}/{max_retries})"
                        )
                        time.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                    else:
                        raise e
            else:
                print(
                    f"Failed to add batch {i // batch_size + 1} after {max_retries} retries. Skipping..."
                )
        print("Ingestion complete. Documents added to vector store (auto-persisted)")
    except Exception as e:
        print(f"An error occurred during vector store ingestion: {e}")


def load_to_vectorstore():
    print("--- Starting Markdown Grant Ingestion Process ---")
    processed_data = load_processed_data(PROCESSED_JSON_PATH)
    langchain_docs = create_langchain_documents(processed_data)
    doc_splits = split_documents(langchain_docs)
    ingest_to_vectorstore(doc_splits)
    print("--- Ingestion Process Finished ---")


load_to_vectorstore()
