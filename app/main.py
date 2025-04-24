# Use standard logging setup
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.chat.router import router as chat_router
from app.common.mongo import get_mongo_client
from app.common.tracing import TraceIdMiddleware
from app.example.router import router as example_router
from app.health.router import router as health_router

# --- Configure logging (ensure this is done) ---
# Example basic config (replace with your preferred setup if needed):
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Or use dictConfig if you have a config class/dict

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    client = await get_mongo_client()
    logger.info("MongoDB client connected")
    yield
    # Shutdown
    if client:
        # Motor's close is not awaitable according to docs
        client.close()  # Corrected based on Motor docs
        logger.info("MongoDB client closed")


app = FastAPI(lifespan=lifespan)

# Setup middleware
app.add_middleware(TraceIdMiddleware)

# Setup Routes
app.include_router(health_router)
app.include_router(example_router)
app.include_router(chat_router)

logger.info("Application startup complete with query endpoint.")


# Optional: Root endpoint
@app.get("/")
async def read_root():
    return {"message": "AI RAG Chatbot Backend is running."}
