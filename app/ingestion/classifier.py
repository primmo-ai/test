import logging
import re

from app.ingestion.parser import ParsedDocument

logger = logging.getLogger(__name__)

# Document types
DOC_TYPE_COMPROMIS = "compromis_vente"
DOC_TYPE_IDENTITE = "piece_identite"
DOC_TYPE_JUSTIF_EDF = "justificatif_domicile_edf"
DOC_TYPE_JUSTIF_IMPOT = "justificatif_domicile_impot"
DOC_TYPE_DPE = "dpe"
DOC_TYPE_UNKNOWN = "inconnu"

# Header-based patterns (checked against first 300 chars of text, case-insensitive)
_HEADER_PATTERNS: list[tuple[str, str]] = [
    (r"compromis\s+de\s+vente", DOC_TYPE_COMPROMIS),
    (r"diagnostic\s+de\s+performance\s+[eé]nerg[eé]tique", DOC_TYPE_DPE),
    (r"avis\s+d.imposition", DOC_TYPE_JUSTIF_IMPOT),
    (r"carte\s+[nm]a[it]ionale\s+d.id", DOC_TYPE_IDENTITE),  # handles OCR typos
    (r"\bedf\b", DOC_TYPE_JUSTIF_EDF),
]

# Filename-based fallback patterns
_FILENAME_PATTERNS: list[tuple[str, str]] = [
    (r"compromis", DOC_TYPE_COMPROMIS),
    (r"dpe|diag", DOC_TYPE_DPE),
    (r"avis_imposition|impot", DOC_TYPE_JUSTIF_IMPOT),
    (r"edf|facture", DOC_TYPE_JUSTIF_EDF),
    (r"identite|piece_id|scan_id|cni", DOC_TYPE_IDENTITE),
    (r"justif|domicile", DOC_TYPE_JUSTIF_EDF),  # generic proof of address fallback
]


def classify_document(doc: ParsedDocument) -> str:
    """Classify a parsed document by type using header text and filename heuristics."""
    header = doc.text[:300].lower()

    # Try header-based classification first
    for pattern, doc_type in _HEADER_PATTERNS:
        if re.search(pattern, header):
            logger.debug("Classified %s as %s (header match)", doc.filename, doc_type)
            return doc_type

    # Fallback to filename-based classification
    fname = doc.filename.lower()
    for pattern, doc_type in _FILENAME_PATTERNS:
        if re.search(pattern, fname):
            logger.debug("Classified %s as %s (filename match)", doc.filename, doc_type)
            return doc_type

    logger.warning("Could not classify %s, marking as unknown", doc.filename)
    return DOC_TYPE_UNKNOWN
