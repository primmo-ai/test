from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    dossier: str | None = None
    doc_types: list[str] | None = None


class Source(BaseModel):
    dossier: str
    doc_type: str
    filename: str
    section: str | None = None
    relevance_score: float


class QueryMetrics(BaseModel):
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_eur: float
    retrieval_count: int


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    metrics: QueryMetrics


class DocumentInfo(BaseModel):
    filename: str
    doc_type: str
    chunks: int
    ocr_confidence: float


class DocumentsResponse(BaseModel):
    dossiers: dict[str, list[DocumentInfo]]
    total_documents: int
    total_chunks: int


class MetricsSummary(BaseModel):
    total_queries: int
    avg_latency_ms: float
    total_cost_eur: float
    budget_remaining_eur: float


class MetricsResponse(BaseModel):
    summary: MetricsSummary
    recent_queries: list[dict]


class HealthResponse(BaseModel):
    status: str
    documents_ingested: int
    chunks_indexed: int
    qdrant_connected: bool
