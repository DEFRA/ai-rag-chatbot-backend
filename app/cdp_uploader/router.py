import os
from tempfile import NamedTemporaryFile

import boto3
from fastapi import APIRouter, HTTPException, Request
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.rag.vector_store import vector_store_grants

router = APIRouter()


@router.post("/uploader-callback")
async def uploader_callback(request: Request):
    """
    Endpoint to receive callback from CDP-Uploader when a file is uploaded and scanned.
    Downloads the file from S3 (LocalStack) and ingests it into the vector store.
    """
    data = await request.json()
    form = data.get("form", {})
    files = [
        v
        for v in form.values()
        if isinstance(v, dict) and v.get("fileStatus") == "complete"
    ]
    if not files:
        raise HTTPException(status_code=400, detail="No completed files in callback.")

    # S3 config for LocalStack
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("LOCALSTACK_ENDPOINT", "http://localstack:4566"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        region_name=os.environ.get("AWS_REGION", "eu-west-2"),
    )

    for file_info in files:
        bucket = file_info["s3Bucket"]
        key = file_info["s3Key"]
        # Download file to temp location
        with NamedTemporaryFile(delete=False) as tmp:
            s3.download_fileobj(bucket, key, tmp)
            tmp_path = tmp.name
        # Load and split document
        loader = TextLoader(tmp_path)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        doc_splits = splitter.split_documents(docs)
        # Ingest to vector store
        if vector_store_grants:
            vector_store_grants.add_documents(doc_splits)
        os.remove(tmp_path)
    return {"status": "success", "files_ingested": len(files)}
