"""Offline retrieval evaluation suite.

Loads ground truth from evals/dataset.json, runs queries through the retriever,
and computes recall, precision, and MRR against expected sources.

Requires: Qdrant running with ingested documents.
Does NOT require: LLM / OpenRouter.
"""

import json
import logging
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

DATASET_PATH = Path("evals/dataset.json")

# --- Thresholds ---
RECALL_THRESHOLD = 0.8
PRECISION_THRESHOLD = 0.5


def _source_matches(retrieved: dict, expected: dict) -> bool:
    """Check if a retrieved chunk matches an expected source."""
    meta = retrieved["metadata"]
    if meta.get("dossier") != expected["dossier"]:
        return False
    if meta.get("filename") != expected["filename"]:
        return False
    if "section" in expected and expected["section"] is not None:
        if meta.get("section") != expected["section"]:
            return False
    return True


def _compute_recall(retrieved: list[dict], expected: list[dict]) -> float:
    """Fraction of expected sources found in retrieved results."""
    if not expected:
        return 1.0
    found = sum(
        1 for exp in expected
        if any(_source_matches(ret, exp) for ret in retrieved)
    )
    return found / len(expected)


def _compute_precision(retrieved: list[dict], expected: list[dict]) -> float:
    """Fraction of retrieved chunks that match an expected source."""
    if not retrieved:
        return 0.0
    matched = sum(
        1 for ret in retrieved
        if any(_source_matches(ret, exp) for exp in expected)
    )
    return matched / len(retrieved)


def _compute_mrr(retrieved: list[dict], expected: list[dict]) -> float:
    """Mean Reciprocal Rank: 1/rank of the first expected source found."""
    for i, ret in enumerate(retrieved):
        if any(_source_matches(ret, exp) for exp in expected):
            return 1.0 / (i + 1)
    return 0.0


# --- Unit tests for metric helpers ---


class TestSourceMatches:
    def test_match_dossier_and_filename(self):
        retrieved = {"metadata": {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}}
        expected = {"dossier": "dossier_1", "filename": "compromis.json"}
        assert _source_matches(retrieved, expected) is True

    def test_match_with_section(self):
        retrieved = {"metadata": {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}}
        expected = {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
        assert _source_matches(retrieved, expected) is True

    def test_no_match_wrong_section(self):
        retrieved = {"metadata": {"dossier": "dossier_1", "filename": "compromis.json", "section": "article_2_prix"}}
        expected = {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
        assert _source_matches(retrieved, expected) is False

    def test_no_match_wrong_dossier(self):
        retrieved = {"metadata": {"dossier": "dossier_2", "filename": "compromis.json", "section": "preambule"}}
        expected = {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
        assert _source_matches(retrieved, expected) is False


class TestMetrics:
    def _chunk(self, dossier: str, filename: str, section: str | None = None) -> dict:
        return {"metadata": {"dossier": dossier, "filename": filename, "section": section}}

    def test_recall_all_found(self):
        retrieved = [self._chunk("dossier_1", "compromis.json", "preambule")]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}]
        assert _compute_recall(retrieved, expected) == 1.0

    def test_recall_none_found(self):
        retrieved = [self._chunk("dossier_2", "dpe_bien.json")]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json"}]
        assert _compute_recall(retrieved, expected) == 0.0

    def test_recall_partial(self):
        retrieved = [self._chunk("dossier_1", "compromis.json")]
        expected = [
            {"dossier": "dossier_1", "filename": "compromis.json"},
            {"dossier": "dossier_1", "filename": "piece_identite_3.json"},
        ]
        assert _compute_recall(retrieved, expected) == 0.5

    def test_precision_all_relevant(self):
        retrieved = [self._chunk("dossier_1", "compromis.json")]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json"}]
        assert _compute_precision(retrieved, expected) == 1.0

    def test_precision_half_relevant(self):
        retrieved = [
            self._chunk("dossier_1", "compromis.json"),
            self._chunk("dossier_1", "diag_dpe.json"),
        ]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json"}]
        assert _compute_precision(retrieved, expected) == 0.5

    def test_mrr_first_position(self):
        retrieved = [self._chunk("dossier_1", "compromis.json")]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json"}]
        assert _compute_mrr(retrieved, expected) == 1.0

    def test_mrr_third_position(self):
        retrieved = [
            self._chunk("dossier_1", "diag_dpe.json"),
            self._chunk("dossier_1", "facture_edf_02.json"),
            self._chunk("dossier_1", "compromis.json"),
        ]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json"}]
        assert _compute_mrr(retrieved, expected) == pytest.approx(1 / 3)

    def test_mrr_not_found(self):
        retrieved = [self._chunk("dossier_1", "diag_dpe.json")]
        expected = [{"dossier": "dossier_1", "filename": "compromis.json"}]
        assert _compute_mrr(retrieved, expected) == 0.0
