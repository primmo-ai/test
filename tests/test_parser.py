from pathlib import Path

from app.ingestion.classifier import (
    DOC_TYPE_COMPROMIS,
    DOC_TYPE_DPE,
    DOC_TYPE_IDENTITE,
    DOC_TYPE_JUSTIF_EDF,
    DOC_TYPE_JUSTIF_IMPOT,
    classify_document,
)
from app.ingestion.parser import parse_all_documents, parse_vision_json

DOCUMENTS_PATH = "documents"


def test_parse_single_document():
    doc = parse_vision_json(Path("documents/dossier_1/compromis.json"))
    assert doc.text
    assert len(doc.text) > 1000
    assert doc.dossier == "dossier_1"
    assert doc.filename == "compromis.json"
    assert doc.avg_confidence > 0.5
    assert doc.page_count >= 1


def test_parse_all_documents():
    docs = parse_all_documents(DOCUMENTS_PATH)
    assert len(docs) == 21


def test_classify_compromis():
    doc = parse_vision_json(Path("documents/dossier_1/compromis.json"))
    assert classify_document(doc) == DOC_TYPE_COMPROMIS


def test_classify_dpe():
    doc = parse_vision_json(Path("documents/dossier_1/diag_dpe.json"))
    assert classify_document(doc) == DOC_TYPE_DPE


def test_classify_identite():
    doc = parse_vision_json(Path("documents/dossier_1/piece_identite_3.json"))
    assert classify_document(doc) == DOC_TYPE_IDENTITE


def test_classify_edf():
    doc = parse_vision_json(Path("documents/dossier_1/facture_edf_02.json"))
    assert classify_document(doc) == DOC_TYPE_JUSTIF_EDF


def test_classify_impot():
    doc = parse_vision_json(Path("documents/dossier_1/avis_imposition.json"))
    assert classify_document(doc) == DOC_TYPE_JUSTIF_IMPOT


def test_classify_low_confidence_identity():
    """scan_006.json has garbled OCR but should still be classified as identity."""
    doc = parse_vision_json(Path("documents/dossier_3/scan_006.json"))
    assert classify_document(doc) == DOC_TYPE_IDENTITE
    assert doc.avg_confidence < 0.5


def test_classify_all_documents():
    """Every document should be classified (no unknowns)."""
    docs = parse_all_documents(DOCUMENTS_PATH)
    for doc in docs:
        doc_type = classify_document(doc)
        assert doc_type != "inconnu", f"{doc.dossier}/{doc.filename} classified as unknown"
