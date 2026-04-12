from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "notarial_documents"

    # Embedding
    embedding_model: str = "intfloat/multilingual-e5-base"

    # RAG
    retrieval_top_k: int = 8
    max_context_chunks: int = 15

    # Documents
    documents_path: str = "/app/documents"

    # Metrics
    metrics_db_path: str = "/app/data/metrics.db"
    budget_limit_eur: float = 20.0

    # Cost rates (EUR per 1M tokens via OpenRouter)
    input_token_rate: float = 3.0
    output_token_rate: float = 15.0

    model_config = {"env_file": ".env"}


settings = Settings()
