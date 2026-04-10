import logging

from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
        dim_fn = getattr(_model, "get_embedding_dimension", None) or _model.get_sentence_embedding_dimension
        logger.info("Embedding model loaded (dim=%d)", dim_fn())
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed document passages with the 'passage:' prefix for E5 models."""
    model = get_model()
    prefixed = [f"passage: {t}" for t in texts]
    embeddings = model.encode(prefixed, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a query with the 'query:' prefix for E5 models."""
    model = get_model()
    embedding = model.encode(f"query: {text}", normalize_embeddings=True)
    return embedding.tolist()
