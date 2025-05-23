import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.rag.ingest_markdown_docs import ingest_uploaded_file
from app.core.rag.vector_store import reload_vector_store

# Set uploads directory to /app/uploads (relative to this file)
UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/cdp-upload", tags=["cdp-upload"])


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    # Validate file type (simple example: allow only .pdf, .txt, .md)
    allowed_ext = {".pdf", ".txt", ".md"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)
    # Trigger ingestion (async or background task in production)
    try:
        ingest_uploaded_file(save_path)
        reload_vector_store()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}") from e
    return JSONResponse({"filename": file.filename, "status": "uploaded and ingested"})
