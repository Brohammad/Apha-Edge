from enum import StrEnum

TIER_LIMITS: dict[str, int] = {
    "anonymous": 30,
    "free": 60,
    "standard": 300,
    "pro": 1000,
    "unlimited": 10_000,
}

RATE_LIMIT_WINDOW_SECONDS = 60

# Paths exempt from rate limiting
RATE_LIMIT_EXEMPT_PREFIXES = (
    "/api/v1/health/",
    "/api/v1/metrics",
    "/api/v1/docs",
    "/api/v1/openapi.json",
)


class RateLimitTier(StrEnum):
    FREE = "free"
    STANDARD = "standard"
    PRO = "pro"
    UNLIMITED = "unlimited"
