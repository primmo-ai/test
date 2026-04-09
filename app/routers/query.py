import logging
import time

from fastapi import APIRouter, HTTPException

from app.main import ingestion_state
from app.metrics.tracker import log_query
from app.models import QueryMetrics, QueryRequest, QueryResponse, Source
from app.rag.chain import query_llm
from app.rag.embeddings import embed_query
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if ingestion_state["status"] != "ready":
        raise HTTPException(status_code=503, detail=f"Service not ready: {ingestion_state['status']}")

    start = time.monotonic()

    # Retrieve relevant chunks
    t0 = time.monotonic()
    chunks = retrieve(
        question=request.question,
        dossier_override=request.dossier,
        doc_types_override=request.doc_types,
    )
    retrieval_ms = int((time.monotonic() - t0) * 1000)

    if not chunks:
        raise HTTPException(status_code=404, detail="Aucun document pertinent trouvé")

    # Query LLM
    llm_response = query_llm(request.question, chunks)

    total_ms = int((time.monotonic() - start) * 1000)
    embedding_ms = retrieval_ms  # embedding is part of retrieval

    # Build sources from retrieved chunks
    sources = []
    seen = set()
    for chunk in chunks:
        meta = chunk["metadata"]
        key = (meta.get("dossier"), meta.get("filename"), meta.get("section"))
        if key not in seen:
            seen.add(key)
            sources.append(Source(
                dossier=meta.get("dossier", ""),
                doc_type=meta.get("doc_type", ""),
                filename=meta.get("filename", ""),
                section=meta.get("section"),
                relevance_score=round(chunk.get("score", 0), 4),
            ))

    # Log metrics
    log_query(
        question=request.question,
        answer=llm_response.answer,
        latency_ms=total_ms,
        embedding_ms=embedding_ms,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_response.llm_latency_ms,
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        cost_eur=llm_response.cost_eur,
        retrieval_count=len(chunks),
        dossier_filter=request.dossier,
        sources=[s.model_dump() for s in sources],
    )

    return QueryResponse(
        answer=llm_response.answer,
        sources=sources,
        metrics=QueryMetrics(
            latency_ms=total_ms,
            input_tokens=llm_response.input_tokens,
            output_tokens=llm_response.output_tokens,
            cost_eur=llm_response.cost_eur,
            retrieval_count=len(chunks),
        ),
    )
