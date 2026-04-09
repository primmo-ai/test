import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        logger.info("Connected to Qdrant at %s:%d", settings.qdrant_host, settings.qdrant_port)
    return _client


def collection_exists() -> bool:
    client = get_client()
    collections = client.get_collections().collections
    return any(c.name == settings.qdrant_collection for c in collections)


def create_collection(vector_size: int) -> None:
    client = get_client()
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )
    # Create payload indexes for filtered search
    for field in ["dossier", "doc_type"]:
        client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name=field,
            field_schema=PayloadSchemaType.KEYWORD,
        )
    client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="parties",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    logger.info("Created collection '%s' with vector size %d", settings.qdrant_collection, vector_size)


def upsert_chunks(
    ids: list[int],
    vectors: list[list[float]],
    payloads: list[dict],
) -> None:
    client = get_client()
    points = [
        PointStruct(id=id_, vector=vec, payload=payload)
        for id_, vec, payload in zip(ids, vectors, payloads)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    logger.info("Upserted %d points to collection", len(points))


def search(
    query_vector: list[float],
    top_k: int = 8,
    dossier: str | None = None,
    doc_types: list[str] | None = None,
    parties: list[str] | None = None,
) -> list[dict]:
    """Search for similar chunks with optional metadata filters."""
    client = get_client()

    must_conditions = []
    if dossier:
        must_conditions.append(FieldCondition(key="dossier", match=MatchValue(value=dossier)))
    if doc_types:
        must_conditions.append(FieldCondition(key="doc_type", match=MatchAny(any=doc_types)))
    if parties:
        must_conditions.append(FieldCondition(key="parties", match=MatchAny(any=parties)))

    query_filter = Filter(must=must_conditions) if must_conditions else None

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "score": hit.score,
            "text": hit.payload.get("text", ""),
            "metadata": {k: v for k, v in hit.payload.items() if k != "text"},
        }
        for hit in results.points
    ]


def get_all_chunks_for_dossier(dossier: str) -> list[dict]:
    """Retrieve all chunks for a specific dossier (for coherence questions)."""
    client = get_client()
    results, _ = client.scroll(
        collection_name=settings.qdrant_collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="dossier", match=MatchValue(value=dossier))]
        ),
        limit=100,
        with_payload=True,
    )
    return [
        {
            "score": 1.0,
            "text": point.payload.get("text", ""),
            "metadata": {k: v for k, v in point.payload.items() if k != "text"},
        }
        for point in results
    ]


def get_collection_count() -> int:
    client = get_client()
    info = client.get_collection(settings.qdrant_collection)
    return info.points_count
