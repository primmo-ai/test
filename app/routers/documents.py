import logging
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter

from app.config import settings
from app.ingestion.classifier import classify_document
from app.ingestion.chunker import chunk_document
from app.ingestion.parser import parse_all_documents
from app.models import DocumentInfo, DocumentsResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_cached_response: DocumentsResponse | None = None


@router.get("/api/documents", response_model=DocumentsResponse)
async def list_documents():
    global _cached_response
    if _cached_response is not None:
        return _cached_response

    docs = parse_all_documents(settings.documents_path)
    dossiers: dict[str, list[DocumentInfo]] = defaultdict(list)
    total_chunks = 0

    for doc in docs:
        doc_type = classify_document(doc)
        chunks = chunk_document(doc)
        total_chunks += len(chunks)
        dossiers[doc.dossier].append(DocumentInfo(
            filename=doc.filename,
            doc_type=doc_type,
            chunks=len(chunks),
            ocr_confidence=doc.avg_confidence,
        ))

    _cached_response = DocumentsResponse(
        dossiers=dict(sorted(dossiers.items())),
        total_documents=len(docs),
        total_chunks=total_chunks,
    )
    return _cached_response
