import pytest

from alphaedge.shared.domain.rate_limit import TIER_LIMITS
from alphaedge.shared.infrastructure.rate_limit import RateLimitError, check_rate_limit


@pytest.mark.asyncio
async def test_rate_limit_allows_under_threshold(monkeypatch):
    calls = {"n": 0}

    class FakeRedis:
        async def incr(self, key: str) -> int:
            calls["n"] += 1
            return calls["n"]

        async def expire(self, key: str, ttl: int) -> None:
            pass

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(
        "alphaedge.shared.infrastructure.rate_limit.get_redis",
        fake_get_redis,
    )

    limit = TIER_LIMITS["standard"]
    for _ in range(limit):
        await check_rate_limit("test-client", "standard")

    with pytest.raises(RateLimitError) as exc:
        await check_rate_limit("test-client", "standard")
    assert exc.value.limit == limit
