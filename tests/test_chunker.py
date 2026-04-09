from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.parser import parse_all_documents, parse_vision_json


def test_chunk_compromis_has_articles():
    doc = parse_vision_json(Path("documents/dossier_1/compromis.json"))
    chunks = chunk_document(doc)
    # 1 preamble + 13 articles
    assert len(chunks) == 14
    assert chunks[0].metadata["section"] == "preambule"
    assert "article_1" in chunks[1].metadata["section"]


def test_chunk_compromis_extracts_parties():
    doc = parse_vision_json(Path("documents/dossier_1/compromis.json"))
    chunks = chunk_document(doc)
    parties = chunks[0].metadata["parties"]
    # Should find at least vendeur and acquereur
    assert len(parties) >= 2
    # Check known names from dossier_1
    all_names = " ".join(parties).upper()
    assert "MOREAU" in all_names
    assert "LAURENT" in all_names


def test_chunk_compromis_has_context_header():
    doc = parse_vision_json(Path("documents/dossier_1/compromis.json"))
    chunks = chunk_document(doc)
    # Article chunks should have context header with parties
    article_chunk = chunks[1]
    assert "Vendeur(s):" in article_chunk.text
    assert "Acquéreur(s):" in article_chunk.text


def test_chunk_small_document_single_chunk():
    doc = parse_vision_json(Path("documents/dossier_1/diag_dpe.json"))
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].metadata["doc_type"] == "dpe"
    assert chunks[0].metadata["dossier"] == "dossier_1"


def test_chunk_identity_extracts_name():
    doc = parse_vision_json(Path("documents/dossier_1/piece_identite_3.json"))
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert len(chunks[0].metadata["parties"]) >= 1


def test_chunk_all_documents():
    """All documents should produce at least 1 chunk each."""
    docs = parse_all_documents("documents")
    total_chunks = 0
    for doc in docs:
        chunks = chunk_document(doc)
        assert len(chunks) >= 1, f"{doc.dossier}/{doc.filename} produced 0 chunks"
        total_chunks += len(chunks)
    # 3 compromis * ~14 chunks + 18 small docs * 1 chunk = ~60 chunks
    assert total_chunks >= 50
    print(f"Total chunks: {total_chunks}")


def test_chunk_metadata_completeness():
    """Every chunk should have required metadata fields."""
    docs = parse_all_documents("documents")
    for doc in docs:
        for chunk in chunk_document(doc):
            meta = chunk.metadata
            assert "dossier" in meta
            assert "doc_type" in meta
            assert "filename" in meta
            assert "ocr_confidence" in meta
            assert meta["dossier"].startswith("dossier_")
