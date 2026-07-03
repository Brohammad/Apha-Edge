from fastapi import Request
from starlette.responses import JSONResponse

from alphaedge.config import settings
from alphaedge.shared.domain.rate_limit import RATE_LIMIT_EXEMPT_PREFIXES
from alphaedge.shared.infrastructure.rate_limit import RateLimitError, check_rate_limit


def _client_key(request: Request) -> tuple[str, str]:
    """Return (redis key suffix, tier) for rate limiting."""
    tier = getattr(request.state, "rate_limit_tier", None)
    user_id = getattr(request.state, "user_id", None)
    if tier and user_id:
        return f"user:{user_id}", tier
    if api_key_id := getattr(request.state, "api_key_id", None):
        return f"apikey:{api_key_id}", getattr(request.state, "rate_limit_tier", "standard")
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        client = request.scope.get("client")
        ip = client[0] if client else "unknown"
    return f"ip:{ip}", "anonymous"


async def rate_limit_middleware(request: Request, call_next):
    if not settings.rate_limit_enabled:
        return await call_next(request)

    path = request.url.path
    if any(path.startswith(p) for p in RATE_LIMIT_EXEMPT_PREFIXES):
        return await call_next(request)

    client_key, tier = _client_key(request)
    try:
        await check_rate_limit(client_key, tier)
    except RateLimitError as exc:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": str(exc),
                    "details": {"limit": exc.limit, "retry_after": exc.retry_after},
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    response = await call_next(request)
    limit_val = _tier_limit(tier)
    response.headers["X-RateLimit-Limit"] = str(limit_val)
    return response


def _tier_limit(tier: str) -> int:
    from alphaedge.shared.domain.rate_limit import TIER_LIMITS

    return TIER_LIMITS.get(tier, TIER_LIMITS["standard"])
