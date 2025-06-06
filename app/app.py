from app.core.rag.download_farming_grants import fetch_and_convert_grant_data
from app.core.rag.ingest_markdown_docs import load_to_vectorstore


def main():
    print("Fetching and converting farming grants data...")
    fetch_and_convert_grant_data()
    print("Loading processed data into vector store...")
    load_to_vectorstore()

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8085, log_config="logging.json")  # noqa: S104


if __name__ == "__main__":
    main()
