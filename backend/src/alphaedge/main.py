import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from sqlalchemy import text
from starlette.responses import Response

from alphaedge.config import settings
from alphaedge.modules.backtesting.presentation.router import backtest_router
from alphaedge.modules.collaboration.presentation.router import collaboration_router
from alphaedge.modules.execution.presentation.router import (
    broker_connections_router,
    orders_router,
)
from alphaedge.modules.identity.presentation.router import router as auth_router
from alphaedge.modules.insights.presentation.router import insights_router
from alphaedge.modules.market_data.presentation.router import (
    instruments_router,
    market_data_router,
)
from alphaedge.modules.market_data.presentation.ws import ws_router
from alphaedge.modules.marketplace.presentation.router import marketplace_router
from alphaedge.modules.optimization.presentation.router import optimization_router
from alphaedge.modules.organization.presentation.router import organizations_router
from alphaedge.modules.payments.presentation.router import payments_router
from alphaedge.modules.portfolio.presentation.router import portfolios_router
from alphaedge.modules.risk.presentation.router import risk_router
from alphaedge.modules.strategy.presentation.router import (
    indicators_router,
    strategies_router,
)
from alphaedge.shared.domain.exceptions import AuthenticationError, DomainException
from alphaedge.shared.infrastructure.database import engine
from alphaedge.shared.infrastructure.logging import setup_logging
from alphaedge.shared.infrastructure.redis import check_redis_health, close_redis
from alphaedge.shared.presentation.auth_context_middleware import auth_context_middleware
from alphaedge.shared.presentation.rate_limit_middleware import rate_limit_middleware

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings.validate_security()
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    docs_url = None if settings.is_production else "/api/v1/docs"
    openapi_url = None if settings.is_production else "/api/v1/openapi.json"

    app = FastAPI(
        title="AlphaEdge API",
        version="0.1.0",
        description="Quantitative trading research and execution platform",
        docs_url=docs_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start
        endpoint = request.url.path
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)

        response.headers["X-Request-ID"] = request_id
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    app.middleware("http")(auth_context_middleware)
    app.middleware("http")(rate_limit_middleware)

    register_exception_handlers(app)
    register_routes(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        status_code = _domain_error_status(exc)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": None,
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = None if settings.is_production else {"errors": exc.errors()}
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": None,
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )


def _domain_error_status(exc: DomainException) -> int:
    mapping = {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
        "AUTHORIZATION_ERROR": status.HTTP_403_FORBIDDEN,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    }
    return mapping.get(exc.code, status.HTTP_400_BAD_REQUEST)


def register_routes(app: FastAPI) -> None:
    api_v1 = APIRouter(prefix="/api/v1")

    api_v1.include_router(auth_router)
    api_v1.include_router(organizations_router)
    api_v1.include_router(marketplace_router)
    api_v1.include_router(payments_router)
    api_v1.include_router(collaboration_router)
    api_v1.include_router(instruments_router)
    api_v1.include_router(market_data_router)
    api_v1.include_router(strategies_router)
    api_v1.include_router(indicators_router)
    api_v1.include_router(backtest_router)
    api_v1.include_router(optimization_router)
    api_v1.include_router(broker_connections_router)
    api_v1.include_router(orders_router)
    api_v1.include_router(insights_router)
    api_v1.include_router(portfolios_router)
    api_v1.include_router(risk_router)
    api_v1.include_router(ws_router)

    @api_v1.get("/health/live", tags=["Health"])
    async def liveness():
        return {"status": "ok"}

    @api_v1.get("/health/ready", tags=["Health"])
    async def readiness():
        checks: dict[str, Any] = {}
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            checks["database"] = "error"

        checks["redis"] = "ok" if await check_redis_health() else "error"

        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ok" if all_ok else "degraded", "checks": checks},
        )

    @api_v1.get("/metrics", tags=["Observability"], include_in_schema=False)
    async def metrics(
        x_metrics_key: str | None = Header(default=None, alias="X-Metrics-Key"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ):
        if settings.is_production:
            authorized = False
            if settings.metrics_api_key and x_metrics_key == settings.metrics_api_key:
                authorized = True
            elif authorization and authorization.startswith("Bearer "):
                from uuid import UUID

                from alphaedge.modules.identity.application.services import TokenService
                from alphaedge.modules.identity.domain.entities import RoleName
                from alphaedge.modules.identity.infrastructure.models import SQLAlchemyUserRepository
                from alphaedge.shared.infrastructure.database import async_session_factory

                try:
                    payload = TokenService.decode_access_token(authorization[7:])
                    sub = payload.get("sub")
                    if sub and isinstance(sub, str):
                        async with async_session_factory() as session:
                            user = await SQLAlchemyUserRepository(session).get_by_id(UUID(sub))
                            authorized = bool(user and user.has_role(RoleName.ADMIN))
                except Exception:
                    authorized = False
            if not authorized:
                raise AuthenticationError("Metrics endpoint requires authentication")
        return Response(content=generate_latest(), media_type="text/plain")

    app.include_router(api_v1)


app = create_app()
