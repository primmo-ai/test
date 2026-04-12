"""Helper to inspect corpus metadata for building evaluation test cases.

Usage: python -m evals.generate_dataset

Prints metadata per dossier (names, doc types, filenames) to help
manually create new test cases in evals/dataset.json.
"""

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
