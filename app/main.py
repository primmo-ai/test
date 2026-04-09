import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models import HealthResponse

logger = logging.getLogger(__name__)

ingestion_state = {
    "status": "starting",
    "documents_ingested": 0,
    "chunks_indexed": 0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    ingestion_state["status"] = "ready"
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Agent RAG Notarial",
    description="API conversationnelle pour dossiers de vente immobilière",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status=ingestion_state["status"],
        documents_ingested=ingestion_state["documents_ingested"],
        chunks_indexed=ingestion_state["chunks_indexed"],
        qdrant_connected=False,
    )
