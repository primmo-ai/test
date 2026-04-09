import logging
import re
from dataclasses import dataclass, field

from app.ingestion.classifier import DOC_TYPE_COMPROMIS, classify_document
from app.ingestion.parser import ParsedDocument

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


def _extract_parties(preamble: str) -> dict:
    """Extract seller/buyer names and cities from a compromis preamble."""
    parties: dict = {"vendeurs": [], "acquereurs": [], "city": None}

    # Extract vendeur names: lines after "VENDEUR(S)" until "ACQUEREUR"
    vendeur_block = re.search(
        r"VENDEUR\(S\)\s*:\s*(.*?)(?=ACQU[EÉ]REUR|$)", preamble, re.DOTALL
    )
    if vendeur_block:
        names = re.findall(r"(?:M\.|Mme|Mlle)\s+([\w-]+(?:\s+[\w-]+)*\s+[A-ZÀ-Ü]{2,})", vendeur_block.group(1))
        parties["vendeurs"] = names

    # Extract acquereur names
    acquereur_block = re.search(
        r"ACQU[EÉ]REUR\(S\)\s*:\s*(.*?)(?=IL A [EÉ]T[EÉ]|ARTICLE|$)", preamble, re.DOTALL
    )
    if acquereur_block:
        names = re.findall(r"(?:M\.|Mme|Mlle)\s+([\w-]+(?:\s+[\w-]+)*\s+[A-ZÀ-Ü]{2,})", acquereur_block.group(1))
        parties["acquereurs"] = names

    # Extract city from property address (in ARTICLE 1 or preamble)
    city_match = re.search(r"\b(\d{5})\s+([A-ZÀ-Ü][a-zà-ü]+(?:[- ][A-Za-zà-ü]+)*)", preamble)
    if city_match:
        parties["city"] = city_match.group(2)

    return parties


def _chunk_compromis(doc: ParsedDocument, doc_type: str) -> list[Chunk]:
    """Split a compromis de vente into preamble + article chunks."""
    text = doc.text
    base_meta = {
        "dossier": doc.dossier,
        "doc_type": doc_type,
        "filename": doc.filename,
        "ocr_confidence": doc.avg_confidence,
    }

    # Split by ARTICLE markers
    parts = re.split(r"(ARTICLE \d+)", text)
    preamble = parts[0].strip()

    # Extract party information from preamble
    parties = _extract_parties(text)
    all_names = parties["vendeurs"] + parties["acquereurs"]
    base_meta["parties"] = all_names
    if parties["city"]:
        base_meta["city"] = parties["city"]

    chunks = []

    # Preamble chunk
    chunks.append(Chunk(
        text=preamble,
        metadata={**base_meta, "section": "preambule"},
    ))

    # Article chunks: pair ARTICLE N header with its content
    for i in range(1, len(parts), 2):
        header = parts[i].strip()  # "ARTICLE N"
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""

        # Extract article subtitle (e.g., "- DESIGNATION DU BIEN")
        subtitle_match = re.match(r"-\s*(.+?)(?:\n|$)", content)
        subtitle = subtitle_match.group(1).strip() if subtitle_match else ""

        section_name = header.lower().replace(" ", "_")
        if subtitle:
            section_name += "_" + re.sub(r"[^a-z0-9]+", "_", subtitle.lower()).strip("_")

        # Prepend preamble summary (parties) for context
        context_header = (
            f"[{doc.dossier} | Compromis de vente | {header}]\n"
            f"Vendeur(s): {', '.join(parties['vendeurs']) or 'N/A'}\n"
            f"Acquéreur(s): {', '.join(parties['acquereurs']) or 'N/A'}\n\n"
        )

        chunks.append(Chunk(
            text=context_header + header + " " + content,
            metadata={**base_meta, "section": section_name},
        ))

    return chunks


def _chunk_small_document(doc: ParsedDocument, doc_type: str) -> list[Chunk]:
    """Keep small documents as a single chunk with metadata header."""
    metadata = {
        "dossier": doc.dossier,
        "doc_type": doc_type,
        "filename": doc.filename,
        "ocr_confidence": doc.avg_confidence,
        "section": None,
        "parties": [],
        "city": None,
    }

    # Try to extract name from document text
    # Format "M./Mme Prénom NOM" (EDF, tax notices)
    name_match = re.search(r"(?:M\.|Mme|Mlle)\s+([\w-]+(?:\s+[\w-]+)*\s+[A-ZÀ-Ü]{2,})", doc.text)
    if name_match:
        metadata["parties"] = [name_match.group(1)]
    else:
        # Format "Nom : NOM\nPrenom(s) : Prénom" (identity documents)
        nom = re.search(r"Nom\s*:\s*([A-ZÀ-Ü]+)", doc.text)
        prenom = re.search(r"Pr[eé]nom\(?s?\)?\s*:\s*([\w-]+)", doc.text)
        if nom:
            full = f"{prenom.group(1)} {nom.group(1)}" if prenom else nom.group(1)
            metadata["parties"] = [full]

    # Try to extract city
    city_match = re.search(r"\b(\d{5})\s+([A-ZÀ-Ü][a-zà-ü]+(?:[- ][A-Za-zà-ü]+)*)", doc.text)
    if city_match:
        metadata["city"] = city_match.group(2)

    header = f"[{doc.dossier} | {doc_type} | {doc.filename}]\n\n"

    return [Chunk(text=header + doc.text, metadata=metadata)]


def chunk_document(doc: ParsedDocument) -> list[Chunk]:
    """Chunk a document based on its type."""
    doc_type = classify_document(doc)

    if doc_type == DOC_TYPE_COMPROMIS:
        chunks = _chunk_compromis(doc, doc_type)
    else:
        chunks = _chunk_small_document(doc, doc_type)

    logger.info(
        "Chunked %s/%s (%s): %d chunks",
        doc.dossier, doc.filename, doc_type, len(chunks),
    )
    return chunks
