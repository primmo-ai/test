import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParsedDocument:
    text: str
    source_uri: str
    file_path: str
    dossier: str
    filename: str
    page_count: int
    avg_confidence: float
    page_confidences: list[float] = field(default_factory=list)


def _compute_avg_confidence(pages: list[dict]) -> tuple[float, list[float]]:
    """Compute average OCR confidence from page-level data."""
    page_confs = []
    for page in pages:
        conf = page.get("confidence", 0.0)
        if conf:
            page_confs.append(conf)
        else:
            # Fallback: average block-level confidences
            blocks = page.get("blocks", [])
            block_confs = [b.get("confidence", 0.0) for b in blocks if b.get("confidence")]
            if block_confs:
                page_confs.append(sum(block_confs) / len(block_confs))
    avg = sum(page_confs) / len(page_confs) if page_confs else 0.0
    return avg, page_confs


def parse_vision_json(file_path: Path) -> ParsedDocument:
    """Extract text and metadata from a Google Cloud Vision OCR JSON file."""
    with open(file_path) as f:
        data = json.load(f)

    response = data.get("responses", [{}])[0]
    annotation = response.get("fullTextAnnotation", {})

    text = annotation.get("text", "")
    pages = annotation.get("pages", [])
    source_uri = data.get("inputConfig", {}).get("gcsSource", {}).get("uri", "")

    avg_confidence, page_confidences = _compute_avg_confidence(pages)

    # Extract dossier name from path (e.g., documents/dossier_1/file.json -> dossier_1)
    dossier = file_path.parent.name

    return ParsedDocument(
        text=text,
        source_uri=source_uri,
        file_path=str(file_path),
        dossier=dossier,
        filename=file_path.name,
        page_count=len(pages),
        avg_confidence=round(avg_confidence, 4),
        page_confidences=page_confidences,
    )


def parse_all_documents(documents_path: str) -> list[ParsedDocument]:
    """Parse all Vision JSON documents from the documents directory."""
    docs_dir = Path(documents_path)
    documents = []

    for json_file in sorted(docs_dir.rglob("*.json")):
        try:
            doc = parse_vision_json(json_file)
            documents.append(doc)
            logger.info(
                "Parsed %s/%s: %d chars, confidence=%.2f",
                doc.dossier,
                doc.filename,
                len(doc.text),
                doc.avg_confidence,
            )
        except Exception:
            logger.exception("Failed to parse %s", json_file)

    logger.info("Parsed %d documents total", len(documents))
    return documents
