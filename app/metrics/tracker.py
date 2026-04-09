import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_db_path: str | None = None


def _get_db_path() -> str:
    global _db_path
    if _db_path is None:
        _db_path = settings.metrics_db_path
        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
    return _db_path


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the metrics table if it doesn't exist."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            answer_preview TEXT,
            latency_ms INTEGER NOT NULL,
            embedding_ms INTEGER DEFAULT 0,
            retrieval_ms INTEGER DEFAULT 0,
            llm_ms INTEGER DEFAULT 0,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_eur REAL DEFAULT 0,
            retrieval_count INTEGER DEFAULT 0,
            dossier_filter TEXT,
            sources_json TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Metrics database initialized at %s", _get_db_path())


def log_query(
    question: str,
    answer: str,
    latency_ms: int,
    embedding_ms: int,
    retrieval_ms: int,
    llm_ms: int,
    input_tokens: int,
    output_tokens: int,
    cost_eur: float,
    retrieval_count: int,
    dossier_filter: str | None,
    sources: list[dict],
) -> None:
    """Log a query and its metrics to the database."""
    conn = _get_connection()
    conn.execute(
        """INSERT INTO query_metrics
        (timestamp, question, answer_preview, latency_ms, embedding_ms, retrieval_ms, llm_ms,
         input_tokens, output_tokens, cost_eur, retrieval_count, dossier_filter, sources_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            question,
            answer[:200],
            latency_ms,
            embedding_ms,
            retrieval_ms,
            llm_ms,
            input_tokens,
            output_tokens,
            cost_eur,
            retrieval_count,
            dossier_filter,
            json.dumps(sources, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def get_summary() -> dict:
    """Get aggregated metrics summary."""
    conn = _get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) as total_queries,
            COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
            COALESCE(SUM(cost_eur), 0) as total_cost_eur
        FROM query_metrics
    """).fetchone()

    summary = {
        "total_queries": row["total_queries"],
        "avg_latency_ms": round(row["avg_latency_ms"], 1),
        "total_cost_eur": round(row["total_cost_eur"], 6),
        "budget_remaining_eur": round(settings.budget_limit_eur - row["total_cost_eur"], 6),
    }
    conn.close()
    return summary


def get_recent_queries(limit: int = 20) -> list[dict]:
    """Get recent query metrics."""
    conn = _get_connection()
    rows = conn.execute(
        """SELECT timestamp, question, latency_ms, embedding_ms, retrieval_ms, llm_ms,
                  input_tokens, output_tokens, cost_eur, retrieval_count
           FROM query_metrics ORDER BY id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
