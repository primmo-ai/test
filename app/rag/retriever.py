import logging
import re

from app.config import settings
from app.rag.embeddings import embed_query
from app.rag.vectorstore import get_all_chunks_for_dossier, search

logger = logging.getLogger(__name__)


def _extract_dossier(query: str) -> str | None:
    """Extract dossier reference from query text."""
    match = re.search(r"dossier[\s_]?(\d+)", query, re.IGNORECASE)
    if match:
        return f"dossier_{match.group(1)}"
    return None


def _extract_doc_types(query: str) -> list[str] | None:
    """Extract document type filters from query keywords."""
    query_lower = query.lower()
    types = []

    if any(kw in query_lower for kw in ["identit", "cni", "carte d'identite", "piece d'identite"]):
        types.append("piece_identite")
    if any(kw in query_lower for kw in ["compromis", "vente", "acheteur", "vendeur", "acquereur"]):
        types.append("compromis_vente")
    if any(kw in query_lower for kw in ["dpe", "diagnostic", "energetique", "energie"]):
        types.append("dpe")
    if any(kw in query_lower for kw in ["domicile", "justificatif", "edf", "facture", "imposition"]):
        types.extend(["justificatif_domicile_edf", "justificatif_domicile_impot"])

    return types if types else None


def _is_coherence_question(query: str) -> bool:
    """Detect if the query asks about coherence/consistency across documents."""
    keywords = ["incoh", "coherent", "coherence", "conformes", "en ordre", "en regle", "correspond"]
    query_lower = query.lower()
    return any(kw in query_lower for kw in keywords)


def retrieve(
    question: str,
    dossier_override: str | None = None,
    doc_types_override: list[str] | None = None,
) -> list[dict]:
    """Retrieve relevant chunks for a question using query analysis + vector search."""
    # Extract filters from query
    dossier = dossier_override or _extract_dossier(question)
    doc_types = doc_types_override or _extract_doc_types(question)

    logger.info(
        "Retrieving for question=%r, dossier=%s, doc_types=%s, coherence=%s",
        question[:80], dossier, doc_types, _is_coherence_question(question),
    )

    # Special case: coherence questions need ALL chunks from a dossier
    if _is_coherence_question(question) and dossier:
        results = get_all_chunks_for_dossier(dossier)
        logger.info("Coherence mode: retrieved %d chunks for %s", len(results), dossier)
        return results

    # Phase 1: filtered vector search
    query_vector = embed_query(question)
    results = search(
        query_vector=query_vector,
        top_k=settings.retrieval_top_k,
        dossier=dossier,
        doc_types=doc_types,
    )

    # Phase 2: fallback without filters if too few results
    if len(results) < 3 and (dossier or doc_types):
        logger.info("Few results (%d) with filters, retrying without filters", len(results))
        results = search(
            query_vector=query_vector,
            top_k=settings.retrieval_top_k,
        )

    logger.info("Retrieved %d chunks (best score: %.3f)", len(results), results[0]["score"] if results else 0)
    return results
