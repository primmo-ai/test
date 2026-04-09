import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.models import HealthResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ingestion_state = {
    "status": "starting",
    "documents_ingested": 0,
    "chunks_indexed": 0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.ingestion.pipeline import run_ingestion
    from app.rag.vectorstore import collection_exists

    logger.info("Starting application...")
    ingestion_state["status"] = "ingesting"

    try:
        stats = run_ingestion()
        ingestion_state["documents_ingested"] = stats["documents"]
        ingestion_state["chunks_indexed"] = stats["chunks"]
        ingestion_state["status"] = "ready"
        logger.info(
            "Ingestion complete: %d documents, %d chunks",
            stats["documents"],
            stats["chunks"],
        )
    except Exception:
        logger.exception("Ingestion failed")
        ingestion_state["status"] = "error"

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
    from app.rag.vectorstore import collection_exists

    qdrant_ok = False
    try:
        qdrant_ok = collection_exists() or ingestion_state["status"] == "ingesting"
    except Exception:
        pass

    return HealthResponse(
        status=ingestion_state["status"],
        documents_ingested=ingestion_state["documents_ingested"],
        chunks_indexed=ingestion_state["chunks_indexed"],
        qdrant_connected=qdrant_ok,
    )
