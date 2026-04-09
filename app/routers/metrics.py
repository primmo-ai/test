from fastapi import APIRouter

from app.metrics.tracker import get_recent_queries, get_summary
from app.models import MetricsResponse, MetricsSummary

router = APIRouter()


@router.get("/api/metrics", response_model=MetricsResponse)
async def get_metrics(limit: int = 20):
    summary_data = get_summary()
    recent = get_recent_queries(limit=limit)

    return MetricsResponse(
        summary=MetricsSummary(**summary_data),
        recent_queries=recent,
    )
