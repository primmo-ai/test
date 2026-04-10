import logging
import time
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un assistant spécialisé dans l'analyse de dossiers notariaux de vente immobilière.
Tu réponds aux questions des notaires et collaborateurs en te basant UNIQUEMENT sur les documents fournis.

Règles :
- Réponds toujours en français.
- Cite les documents sources (dossier, type de document, nom de fichier) pour chaque information.
- Si l'information n'est pas dans les documents fournis, dis-le clairement.
- Pour les vérifications de conformité, applique ces règles :
  * Pièce d'identité : vérifier la date d'expiration, la correspondance nom/prénom avec le compromis
  * DPE : vérifier qu'il correspond au bien (adresse, surface), qu'il est valide (10 ans)
  * Justificatif de domicile : vérifier qu'il est récent (< 3 mois avant la date du compromis), que le nom correspond
- Signale tout document avec un score OCR faible (< 0.8) qui pourrait contenir des erreurs de lecture.
- Quand tu détectes des incohérences entre documents, liste-les explicitement.
- Structure ta réponse clairement avec des points si nécessaire."""


def _format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into context for the LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        header_parts = [
            f"Dossier: {meta.get('dossier', 'N/A')}",
            f"Type: {meta.get('doc_type', 'N/A')}",
            f"Fichier: {meta.get('filename', 'N/A')}",
        ]
        if meta.get("section"):
            header_parts.append(f"Section: {meta['section']}")
        header_parts.append(f"Confiance OCR: {meta.get('ocr_confidence', 'N/A')}")
        if chunk.get("score") and chunk["score"] < 1.0:
            header_parts.append(f"Pertinence: {chunk['score']:.2f}")

        header = " | ".join(header_parts)
        parts.append(f"[Document {i} | {header}]\n{chunk['text']}")

    return "\n\n---\n\n".join(parts)


@dataclass
class LLMResponse:
    answer: str
    input_tokens: int
    output_tokens: int
    cost_eur: float
    llm_latency_ms: int


def query_llm(question: str, chunks: list[dict]) -> LLMResponse:
    """Send question + context to OpenRouter and return the response."""
    context = _format_context(chunks)

    user_message = f"""Documents pertinents :
---
{context}
---

Question : {question}"""

    start = time.monotonic()

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{settings.openrouter_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0,
            },
        )
        response.raise_for_status()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    data = response.json()

    answer = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Calculate cost in EUR (rates are per 1M tokens)
    cost = (
        input_tokens * settings.input_token_rate / 1_000_000
        + output_tokens * settings.output_token_rate / 1_000_000
    )

    logger.info(
        "LLM response: %d input tokens, %d output tokens, %.4f EUR, %d ms",
        input_tokens, output_tokens, cost, elapsed_ms,
    )

    return LLMResponse(
        answer=answer,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_eur=round(cost, 6),
        llm_latency_ms=elapsed_ms,
    )
