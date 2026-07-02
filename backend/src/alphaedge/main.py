import time
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from sqlalchemy import text
from starlette.responses import Response

from alphaedge.config import settings
from alphaedge.modules.identity.presentation.router import router as auth_router
from alphaedge.shared.domain.exceptions import DomainException
from alphaedge.shared.infrastructure.database import engine
from alphaedge.shared.infrastructure.logging import setup_logging
from alphaedge.shared.infrastructure.redis import check_redis_health, close_redis

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await close_redis()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AlphaEdge API",
        version="0.1.0",
        description="Quantitative trading research and execution platform",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
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
        return response

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
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": exc.errors()},
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
    }
    return mapping.get(exc.code, status.HTTP_400_BAD_REQUEST)


def register_routes(app: FastAPI) -> None:
    api_v1 = APIRouter(prefix="/api/v1")

    api_v1.include_router(auth_router)

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
        except Exception as e:
            checks["database"] = f"error: {e}"

        checks["redis"] = "ok" if await check_redis_health() else "error"

        all_ok = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if all_ok else 503,
            content={"status": "ok" if all_ok else "degraded", "checks": checks},
        )

    @api_v1.get("/metrics", tags=["Observability"], include_in_schema=False)
    async def metrics():
        return Response(content=generate_latest(), media_type="text/plain")

    app.include_router(api_v1)


app = create_app()
