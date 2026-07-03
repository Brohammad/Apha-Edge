import time

from alphaedge.shared.domain.rate_limit import RATE_LIMIT_WINDOW_SECONDS, TIER_LIMITS
from alphaedge.shared.infrastructure.redis import get_redis


class RateLimitError(Exception):
    def __init__(self, limit: int, retry_after: int) -> None:
        self.limit = limit
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded: {limit} requests per minute")


async def check_rate_limit(client_key: str, tier: str) -> None:
    """Redis sliding-window counter; raises RateLimitExceeded when over limit."""
    limit = TIER_LIMITS.get(tier, TIER_LIMITS["standard"])
    if limit >= TIER_LIMITS["unlimited"]:
        return

    redis = await get_redis()
    window = int(time.time()) // RATE_LIMIT_WINDOW_SECONDS
    key = f"rl:{client_key}:{window}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, RATE_LIMIT_WINDOW_SECONDS + 1)

    if count > limit:
        retry_after = RATE_LIMIT_WINDOW_SECONDS - (int(time.time()) % RATE_LIMIT_WINDOW_SECONDS)
        raise RateLimitError(limit, retry_after)
