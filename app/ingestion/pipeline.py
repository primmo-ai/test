import logging

from app.config import settings
from app.ingestion.chunker import chunk_document
from app.ingestion.parser import parse_all_documents
from app.rag.embeddings import embed_passages, get_model
from app.rag.vectorstore import (
    collection_exists,
    create_collection,
    get_collection_count,
    upsert_chunks,
)

logger = logging.getLogger(__name__)


def run_ingestion() -> dict:
    """Parse, chunk, embed, and store all documents. Returns ingestion stats."""
    if collection_exists():
        count = get_collection_count()
        logger.info("Collection already exists with %d points, skipping ingestion", count)
        docs = parse_all_documents(settings.documents_path)
        return {"documents": len(docs), "chunks": count, "skipped": True}

    # Parse all documents
    logger.info("Starting document ingestion from %s", settings.documents_path)
    documents = parse_all_documents(settings.documents_path)

    # Chunk all documents
    all_chunks = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))

    logger.info("Total chunks created: %d", len(all_chunks))

    # Create collection
    model = get_model()
    vector_size = model.get_embedding_dimension()
    create_collection(vector_size)

    # Embed and upsert in batches
    batch_size = 32
    total_upserted = 0

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        texts = [c.text for c in batch]
        vectors = embed_passages(texts)

        payloads = []
        for chunk in batch:
            payload = {**chunk.metadata, "text": chunk.text}
            payloads.append(payload)

        ids = list(range(i, i + len(batch)))
        upsert_chunks(ids, vectors, payloads)
        total_upserted += len(batch)
        logger.info("Upserted batch %d/%d (%d chunks)", i // batch_size + 1, -(-len(all_chunks) // batch_size), len(batch))

    logger.info("Ingestion complete: %d documents, %d chunks indexed", len(documents), total_upserted)
    return {"documents": len(documents), "chunks": total_upserted, "skipped": False}
