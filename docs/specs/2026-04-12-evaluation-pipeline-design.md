# Evaluation Pipeline Design — Notarial RAG Agent

## Context

The notarial RAG agent retrieves document chunks from a Qdrant vector store and generates French-language answers via an LLM. Currently, query metrics (latency, tokens, cost) are tracked, but there is no evaluation of **retrieval accuracy** or **answer quality**. This spec defines an offline retrieval evaluation pipeline to measure and improve the system.

## Scope

**In scope (build now):**
- Ground truth evaluation dataset (`evals/dataset.json`)
- One-time dataset generation script (`evals/generate_dataset.py`)
- Offline retrieval evaluation test suite (`tests/test_eval_retrieval.py`)

**Out of scope (next steps):**
- End-to-end API evaluation (Layer 2)
- LLM-as-judge answer quality scoring (RAGAS / LangSmith)
- CI integration and regression tracking

## Evaluation Dataset

### Format

File: `evals/dataset.json`

```json
[
  {
    "id": "targeted_vendeurs_d1",
    "question": "Qui sont les vendeurs du dossier 1?",
    "category": "targeted",
    "expected_sources": [
      {"dossier": "dossier_1", "filename": "compromis.json", "section": "preambule"}
    ],
    "expected_facts": ["MOREAU", "vendeur"],
    "dossier_filter": "dossier_1",
    "doc_type_filter": null
  }
]
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the test case |
| `question` | string | Natural language query in French |
| `category` | string | `targeted` / `cross_dossier` / `coherence` — maps to the 3 retrieval strategies |
| `expected_sources` | array | Chunks that **must** appear in results. Matched by `dossier` + `filename`, and optionally `section` |
| `expected_facts` | array | Keywords that should appear in retrieved chunk text (lightweight validation) |
| `dossier_filter` | string or null | Explicit dossier filter (tests filter extraction independently) |
| `doc_type_filter` | string or null | Explicit doc_type filter |

### Source matching logic

A retrieved chunk matches an expected source when:
1. `dossier` values are equal
2. `filename` values are equal
3. If `section` is specified in the expectation, it must also match

### Coverage targets

~20-30 test cases:
- ~3 per README query template (one per dossier where applicable)
- ~5 edge cases (low OCR confidence doc, cross-dossier name search, missing document type)
- ~3 coherence/conformity checks

### Seed queries (from README)

1. Dans quel dossier monsieur ... est-il vendeur?
2. Qui sont les acheteurs et les vendeurs sur le dossier ...?
3. Quel est le bien concerne par la transaction de Paris?
4. Les pieces d'identite sont-elles en ordre?
5. Le DPE est-il present et correspond-il au bien?
6. Les justificatifs de domicile sont-ils conformes?
7. Y a-t-il des incoherences entre les documents du dossier ...?

These are instantiated with real dossier data (names, numbers, cities from the parsed documents).

## Dataset Generation Script

File: `evals/generate_dataset.py`

Run once to bootstrap the dataset:

1. Parse all documents to extract real metadata (names, dossiers, cities, doc types)
2. Instantiate the 7 README query templates with real data
3. Use an LLM to generate additional queries from chunk metadata (filenames, doc types, parties, sections per dossier)
4. Output a draft `evals/dataset.json` for human review and curation

After bootstrap, the dataset is hand-maintained — cases are added/edited as the system evolves.

## Retrieval Evaluation Test Suite

File: `tests/test_eval_retrieval.py`

### How it works

1. Loads test cases from `evals/dataset.json`
2. Initializes the retriever stack directly (embeddings + Qdrant client — no FastAPI, no LLM)
3. For each test case, calls the retriever with the question and optional filters
4. Computes per-query metrics (see below)
5. Computes aggregate metrics and prints a summary table
6. Fails if any aggregate metric drops below threshold

### Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| Context Recall | `found_expected / total_expected` | Fraction of expected sources that were actually retrieved |
| Context Precision | `found_expected / total_retrieved` | Fraction of retrieved chunks that were expected |
| MRR (Mean Reciprocal Rank) | `1 / rank_of_first_expected` | How high the first expected source ranks in results |

### Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Context Recall | >= 0.8 | The critical metric. If the system doesn't retrieve the right documents, the LLM can't produce a correct answer. 0.8 tolerates missing 1 expected source out of 5, but not systematic misses. For a notarial tool, missing a relevant document (e.g., an expired identity card) could mean missing a compliance issue. |
| Context Precision | >= 0.5 | Intentionally lenient. Semantic search naturally returns tangentially related chunks (e.g., searching for "vendeurs du dossier 1" may pull the buyer's identity doc because names co-occur). With top-k=8, getting 4+ relevant chunks out of 8 is a reasonable baseline. The LLM can ignore irrelevant context — extra context is less harmful than missing information. |

These are starting thresholds. Real eval data will inform adjustments.

### Prerequisites

- Qdrant running with ingested documents (same as existing test suite)
- No LLM or OpenRouter needed

### Running

```bash
pytest tests/test_eval_retrieval.py -v
```

Separate from unit tests: `pytest tests/ -k "not eval"` to skip evals.

### Output

A summary table printed after the run:

```
Retrieval Evaluation Results
============================================================
ID                          | Recall | Precision | MRR
----------------------------+--------+-----------+------
targeted_vendeurs_d1        |   1.00 |      0.50 | 1.00
cross_dossier_moreau        |   1.00 |      0.25 | 0.33
coherence_d1                |   0.85 |      0.71 | 1.00
...
----------------------------+--------+-----------+------
AGGREGATE                   |   0.92 |      0.53 | 0.78
============================================================
```

## Project Structure

```
evals/
  dataset.json              # Ground truth (curated, checked into git)
  generate_dataset.py       # One-time bootstrap script
tests/
  test_eval_retrieval.py    # Retrieval evaluation suite
  test_parser.py            # (existing)
  test_chunker.py           # (existing)
```

## Next Steps (not built now)

### Layer 2 — End-to-end API evaluation

A pytest suite that sends requests to `POST /api/query` and validates:
- `sources` field against expected sources (same metrics as Layer 1)
- `answer` field against expected facts (keyword presence)

Requires a running stack with LLM access.

### LLM-as-judge answer quality

Integrate RAGAS or LangSmith evaluators to score:
- **Faithfulness** — does the answer stay grounded in the retrieved context?
- **Answer relevancy** — does it address the question asked?
- **Correctness** — does it match a reference answer?

### CI integration

- Layer 1 (retrieval) runs on every PR — fast, deterministic, no cost
- Layer 2 (end-to-end) runs on-demand or nightly

### Regression tracking

Store eval results over time to detect retrieval quality drift when changing:
- Chunking strategy
- Embedding model
- Retrieval parameters (top-k, filters)
- Document corpus
