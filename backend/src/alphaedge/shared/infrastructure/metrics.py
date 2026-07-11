"""Shared Prometheus metrics for AlphaEdge observability."""

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)
RISK_GATE_REJECTIONS = Counter(
    "risk_gate_rejections_total",
    "Orders rejected by the pre-trade risk gate",
    ["stage"],
)
ORDERS_SUBMITTED = Counter(
    "orders_submitted_total",
    "Orders accepted for execution",
    ["side", "order_type"],
)
CELERY_TASKS = Counter(
    "celery_tasks_total",
    "Celery tasks by name and outcome",
    ["task", "outcome"],
)
CELERY_TASK_LATENCY = Histogram(
    "celery_task_duration_seconds",
    "Celery task runtime",
    ["task"],
)
WS_CONNECTIONS = Gauge(
    "websocket_connections_active",
    "Active WebSocket connections",
    ["channel"],
)
WS_MESSAGES = Counter(
    "websocket_messages_total",
    "WebSocket messages sent/received",
    ["channel", "direction"],
)
DB_QUERY_LATENCY = Histogram(
    "db_query_duration_seconds",
    "Database session operation latency",
    ["operation"],
)
