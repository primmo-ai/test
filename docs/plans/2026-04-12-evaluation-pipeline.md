# Evaluation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline retrieval evaluation pipeline with a ground truth dataset and pytest-based metrics (recall, precision, MRR).

**Architecture:** A JSON dataset of test cases (queries + expected sources) feeds a pytest suite that calls the retriever directly (embeddings + Qdrant, no LLM). Metrics are computed per-query and aggregated, with configurable pass/fail thresholds.

**Tech Stack:** Python, pytest, existing app modules (retriever, embeddings, vectorstore, parser, chunker)

**Spec:** `docs/specs/2026-04-12-evaluation-pipeline-design.md`

---

### Task 1: Create the evaluation dataset

**Files:**
- Create: `evals/dataset.json`

This dataset contains 21 test cases covering all 3 categories (targeted, cross_dossier, coherence), all 3 dossiers, and edge cases. Built from real corpus metadata.

- [ ] **Step 1: Create the evals directory and dataset file**

```json
[
  {
    "id": "targeted_vendeurs_d1",
    "question": "Qui sont les vendeurs du dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
    ],
    "expected_facts": ["MOREAU"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  },
  {
    "id": "targeted_acheteurs_d1",
    "question": "Qui sont les acheteurs du dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
    ],
    "expected_facts": ["LAURENT"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  },
  {
    "id": "targeted_vendeurs_d2",
    "question": "Qui sont les vendeurs du dossier 2?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "compromis_vente.json", "section": "preambule"}
    ],
    "expected_facts": ["DUBOIS"],
    "dossier_filter": "dossier_2",
    "doc_type_filter": null
  },
  {
    "id": "targeted_acheteurs_d3",
    "question": "Qui sont les acheteurs du dossier 3?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_3", "filename": "scan_012.json", "section": "preambule"}
    ],
    "expected_facts": ["FONTAINE"],
    "dossier_filter": "dossier_3",
    "doc_type_filter": null
  },
  {
    "id": "targeted_bien_paris",
    "question": "Quel est le bien concerné par la transaction de Paris?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "article_1_designation_du_bien"}
    ],
    "expected_facts": ["Paris", "Lilas"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "targeted_bien_bordeaux",
    "question": "Quel est le bien concerné par la transaction de Bordeaux?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "compromis_vente.json", "section": "article_1_designation_du_bien"}
    ],
    "expected_facts": ["Bordeaux", "Medoc"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "targeted_bien_lyon",
    "question": "Quel est le bien concerné par la transaction de Lyon?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_3", "filename": "scan_012.json", "section": "article_1_designation_du_bien"}
    ],
    "expected_facts": ["Lyon", "Republique"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "targeted_dpe_d1",
    "question": "Le DPE est-il présent dans le dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "diag_dpe.json"}
    ],
    "expected_facts": ["diagnostic", "energie"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  },
  {
    "id": "targeted_dpe_d2",
    "question": "Le DPE correspond-il au bien du dossier 2?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "dpe_bien.json"}
    ],
    "expected_facts": ["diagnostic", "energie"],
    "dossier_filter": "dossier_2",
    "doc_type_filter": null
  },
  {
    "id": "targeted_identite_d1",
    "question": "Les pièces d'identité sont-elles en ordre dans le dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "piece_identite_3.json"},
      {"dossier": "dossier_1", "filename": "scan_id_001.json"}
    ],
    "expected_facts": ["identite"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  },
  {
    "id": "targeted_justif_domicile_d1",
    "question": "Les justificatifs de domicile sont-ils conformes dans le dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "facture_edf_02.json"},
      {"dossier": "dossier_1", "filename": "avis_imposition.json"}
    ],
    "expected_facts": ["domicile"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  },
  {
    "id": "targeted_justif_domicile_d2",
    "question": "Les justificatifs de domicile sont-ils conformes dans le dossier 2?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "justif_domicile_1.json"},
      {"dossier": "dossier_2", "filename": "justif_domicile_2.json"}
    ],
    "expected_facts": ["domicile"],
    "dossier_filter": "dossier_2",
    "doc_type_filter": null
  },
  {
    "id": "cross_dossier_moreau",
    "question": "Dans quel dossier monsieur MOREAU est-il vendeur?",
    "category": "cross_dossier",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
    ],
    "expected_facts": ["MOREAU", "dossier_1"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "cross_dossier_dubois",
    "question": "Dans quel dossier madame DUBOIS est-elle vendeuse?",
    "category": "cross_dossier",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "compromis_vente.json", "section": "preambule"}
    ],
    "expected_facts": ["DUBOIS", "dossier_2"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "cross_dossier_fontaine",
    "question": "Dans quel dossier monsieur FONTAINE est-il acheteur?",
    "category": "cross_dossier",
    "expected_sources": [
      {"dossier": "dossier_3", "filename": "scan_012.json", "section": "preambule"}
    ],
    "expected_facts": ["FONTAINE", "dossier_3"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "cross_dossier_benali",
    "question": "M. BENALI achète dans quelle ville?",
    "category": "cross_dossier",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "compromis_vente.json", "section": "preambule"}
    ],
    "expected_facts": ["BENALI", "Bordeaux"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "coherence_d1",
    "question": "Y a-t-il des incohérences entre les documents du dossier 1?",
    "category": "coherence",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"},
      {"dossier": "dossier_1", "filename": "piece_identite_3.json"},
      {"dossier": "dossier_1", "filename": "facture_edf_02.json"}
    ],
    "expected_facts": ["MOREAU", "LAURENT"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "coherence_d2",
    "question": "Les documents du dossier 2 sont-ils conformes?",
    "category": "coherence",
    "expected_sources": [
      {"dossier": "dossier_2", "filename": "compromis_vente.json", "section": "preambule"},
      {"dossier": "dossier_2", "filename": "piece_id_vendeuse.json"},
      {"dossier": "dossier_2", "filename": "dpe_bien.json"}
    ],
    "expected_facts": ["DUBOIS", "BENALI"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "coherence_d3",
    "question": "Y a-t-il des incohérences dans le dossier 3?",
    "category": "coherence",
    "expected_sources": [
      {"dossier": "dossier_3", "filename": "scan_012.json", "section": "preambule"},
      {"dossier": "dossier_3", "filename": "id_vendeuse.json"},
      {"dossier": "dossier_3", "filename": "scan_006.json"}
    ],
    "expected_facts": ["PETIT", "FONTAINE"],
    "dossier_filter": null,
    "doc_type_filter": null
  },
  {
    "id": "edge_low_ocr_d3",
    "question": "Quelle est la pièce d'identité d'Alexandre FONTAINE dans le dossier 3?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_3", "filename": "scan_006.json"}
    ],
    "expected_facts": ["FONTAINE"],
    "dossier_filter": "dossier_3",
    "doc_type_filter": null
  },
  {
    "id": "edge_prix_vente_d1",
    "question": "Quel est le prix de vente dans le dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "article_2_prix"}
    ],
    "expected_facts": ["prix"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  }
]
```

Write this to `evals/dataset.json`.

- [ ] **Step 2: Commit**

```bash
git add evals/dataset.json
git commit -m "feat: add evaluation dataset with 21 ground truth test cases"
```

---

### Task 2: Write the retrieval evaluation test suite — metrics helpers

**Files:**
- Create: `tests/test_eval_retrieval.py`

We build the test file in two steps: first the metric computation functions with their own unit tests, then the main evaluation loop.

- [ ] **Step 1: Write tests for the metric helper functions**

These test the metric math in isolation, no Qdrant needed.

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_eval_retrieval.py -v -k "TestSourceMatches or TestMetrics"`

Expected: 13 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_eval_retrieval.py
git commit -m "feat: add retrieval eval metric helpers with unit tests"
```

---

### Task 3: Write the retrieval evaluation test suite — main evaluation loop

**Files:**
- Modify: `tests/test_eval_retrieval.py` (append after TestMetrics class)

- [ ] **Step 1: Add the main evaluation test**

Append this after the `TestMetrics` class in `tests/test_eval_retrieval.py`:

```python
# --- Main evaluation ---


def _load_dataset() -> list[dict]:
    """Load evaluation dataset from JSON file."""
    with open(DATASET_PATH) as f:
        return json.load(f)


def _print_results_table(results: list[dict], aggregates: dict) -> None:
    """Print a summary table of evaluation results."""
    header = f"{'ID':<40} | {'Recall':>6} | {'Precision':>9} | {'MRR':>5}"
    separator = "-" * 40 + "-+-" + "-" * 6 + "-+-" + "-" * 9 + "-+-" + "-" * 5
    print("\nRetrieval Evaluation Results")
    print("=" * len(header))
    print(header)
    print(separator)
    for r in results:
        print(f"{r['id']:<40} | {r['recall']:>6.2f} | {r['precision']:>9.2f} | {r['mrr']:>5.2f}")
    print(separator)
    print(f"{'AGGREGATE':<40} | {aggregates['recall']:>6.2f} | {aggregates['precision']:>9.2f} | {aggregates['mrr']:>5.2f}")
    print("=" * len(header))


@pytest.fixture(scope="module")
def qdrant_available():
    """Check that Qdrant is running and has data."""
    from app.rag.vectorstore import collection_exists, get_collection_count

    if not collection_exists():
        pytest.skip("Qdrant collection not found — run ingestion first")
    count = get_collection_count()
    if count == 0:
        pytest.skip("Qdrant collection is empty — run ingestion first")
    return count


@pytest.mark.eval
class TestRetrievalEvaluation:
    """Run the full retrieval evaluation against the ground truth dataset.

    Requires Qdrant running with ingested documents.
    Run with: pytest tests/test_eval_retrieval.py -v -m eval
    Skip with: pytest tests/ -m "not eval"
    """

    def test_retrieval_quality(self, qdrant_available):
        from app.rag.retriever import retrieve

        dataset = _load_dataset()
        results = []

        for case in dataset:
            chunks = retrieve(
                question=case["question"],
                dossier_override=case.get("dossier_filter"),
                doc_types_override=[case["doc_type_filter"]] if case.get("doc_type_filter") else None,
            )

            recall = _compute_recall(chunks, case["expected_sources"])
            precision = _compute_precision(chunks, case["expected_sources"])
            mrr = _compute_mrr(chunks, case["expected_sources"])

            results.append({
                "id": case["id"],
                "recall": recall,
                "precision": precision,
                "mrr": mrr,
            })

        # Compute aggregates
        n = len(results)
        aggregates = {
            "recall": sum(r["recall"] for r in results) / n,
            "precision": sum(r["precision"] for r in results) / n,
            "mrr": sum(r["mrr"] for r in results) / n,
        }

        _print_results_table(results, aggregates)

        # Assert thresholds
        assert aggregates["recall"] >= RECALL_THRESHOLD, (
            f"Aggregate recall {aggregates['recall']:.2f} below threshold {RECALL_THRESHOLD}"
        )
        assert aggregates["precision"] >= PRECISION_THRESHOLD, (
            f"Aggregate precision {aggregates['precision']:.2f} below threshold {PRECISION_THRESHOLD}"
        )
```

- [ ] **Step 2: Run the metric helper tests to verify nothing broke**

Run: `pytest tests/test_eval_retrieval.py -v -k "TestSourceMatches or TestMetrics"`

Expected: 13 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_eval_retrieval.py
git commit -m "feat: add main retrieval evaluation test with Qdrant integration"
```

---

### Task 4: Configure pytest markers and verify full suite

**Files:**
- Create: `pytest.ini` (or modify if exists)

- [ ] **Step 1: Check if pytest config exists**

Run: `ls pytest.ini pyproject.toml setup.cfg 2>/dev/null`

Check if any of these already has `[tool.pytest]` or `[pytest]` config.

- [ ] **Step 2: Add the eval marker**

If `pyproject.toml` exists and has pytest config, add there. Otherwise create `pytest.ini`:

```ini
[pytest]
markers =
    eval: Retrieval evaluation tests (require Qdrant with ingested data)
```

- [ ] **Step 3: Run existing unit tests to verify no regression**

Run: `pytest tests/ -v -m "not eval"`

Expected: 16 existing tests PASS (9 parser + 7 chunker)

- [ ] **Step 4: Commit**

```bash
git add pytest.ini
git commit -m "feat: add pytest eval marker for retrieval evaluation tests"
```

---

### Task 5: Run the full evaluation against live Qdrant

This task requires the Docker stack running with ingested documents.

- [ ] **Step 1: Start the stack (if not already running)**

Run: `make run-ollama` (or `make run` if using OpenRouter)

Wait for the health endpoint to report ready:

Run: `curl -s http://localhost:8000/api/health | python -m json.tool`

Expected: `"status": "ready"` with `documents_ingested: 21`

- [ ] **Step 2: Set Qdrant connection for local access**

The tests need to connect to Qdrant directly. If running via Docker, Qdrant is on localhost:6333:

Run: `QDRANT_HOST=localhost pytest tests/test_eval_retrieval.py -v -m eval`

- [ ] **Step 3: Review the results table**

Check the output table. For each row:
- Recall < 0.8 → the retriever is missing expected documents for that query
- Precision < 0.3 → the retriever is returning too much noise
- MRR < 0.5 → the expected document is ranked too low

- [ ] **Step 4: Adjust dataset if needed**

If a test case has wrong expectations (e.g., `section` name doesn't match actual chunk section), fix `evals/dataset.json` and re-run. The dataset is ground truth — it must be accurate.

- [ ] **Step 5: Commit any dataset fixes**

```bash
git add evals/dataset.json
git commit -m "fix: correct evaluation dataset after first live run"
```

(Skip this step if no fixes were needed.)

---

### Task 6: Generate additional test cases (optional bootstrap)

**Files:**
- Create: `evals/generate_dataset.py`

A helper script that extracts metadata from the corpus and prints candidate test cases. Not automated LLM generation — just a helper to inspect what data is available.

- [ ] **Step 1: Write the generation helper**

```python
"""Helper to inspect corpus metadata for building evaluation test cases.

Usage: python -m evals.generate_dataset

Prints metadata per dossier (names, doc types, filenames) to help
manually create new test cases in evals/dataset.json.
"""

import json
from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.classifier import classify_document
from app.ingestion.parser import parse_all_documents


def main() -> None:
    docs = parse_all_documents("documents")

    # Group by dossier
    dossiers: dict[str, list] = {}
    for doc in docs:
        dossiers.setdefault(doc.dossier, []).append(doc)

    for dossier, dossier_docs in sorted(dossiers.items()):
        print(f"\n{'='*60}")
        print(f"  {dossier}")
        print(f"{'='*60}")

        for doc in dossier_docs:
            doc_type = classify_document(doc)
            chunks = chunk_document(doc)
            parties = set()
            city = None
            sections = []

            for chunk in chunks:
                meta = chunk.metadata
                for p in meta.get("parties", []):
                    parties.add(p)
                if meta.get("city"):
                    city = meta["city"]
                if meta.get("section"):
                    sections.append(meta["section"])

            print(f"\n  {doc.filename}")
            print(f"    type: {doc_type}")
            print(f"    confidence: {doc.avg_confidence:.2f}")
            print(f"    chunks: {len(chunks)}")
            if parties:
                print(f"    parties: {', '.join(sorted(parties))}")
            if city:
                print(f"    city: {city}")
            if sections:
                print(f"    sections: {', '.join(sections)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create `evals/__init__.py`**

Create an empty `evals/__init__.py` so the module is importable.

- [ ] **Step 3: Run the script**

Run: `python -m evals.generate_dataset`

Expected: prints metadata for all 21 documents across 3 dossiers — names, types, sections, confidence scores.

- [ ] **Step 4: Commit**

```bash
git add evals/generate_dataset.py evals/__init__.py
git commit -m "feat: add dataset generation helper for corpus metadata inspection"
```
