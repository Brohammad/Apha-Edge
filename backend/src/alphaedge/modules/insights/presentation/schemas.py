from datetime import datetime

from pydantic import BaseModel


class RequestInsightRequest(BaseModel):
    insight_type: str
    source_type: str
    source_id: str


class StrategyExplainRequest(BaseModel):
    strategy_id: str | None = None
    strategy_version_id: str | None = None


class PerformanceReportRequest(BaseModel):
    backtest_run_id: str


class AskInsightRequest(BaseModel):
    question: str
    context_type: str | None = None
    context_id: str | None = None


class AskInsightResponse(BaseModel):
    answer: str
    sources: list[dict[str, str]] = []


class InsightRequestResponse(BaseModel):
    id: str
    user_id: str
    insight_type: str
    source_type: str
    source_id: str
    status: str
    error_message: str | None
    celery_task_id: str | None
    created_at: datetime
    updated_at: datetime


class InsightReportResponse(BaseModel):
    id: str
    insight_request_id: str
    content: str
    metadata: dict[str, object]
    created_at: datetime


class InsightDetailResponse(BaseModel):
    request: InsightRequestResponse
    report: InsightReportResponse | None = None
