import pytest

from alphaedge.modules.market_data.infrastructure.quotes import AlphaVantageQuoteClient
from alphaedge.shared.domain.exceptions import ValidationError


@pytest.mark.asyncio
async def test_alpha_vantage_information_field_raises(monkeypatch):
    client = AlphaVantageQuoteClient()

    async def fake_get(*_args, **_kwargs):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "Information": (
                        "We have detected your API key and our standard API rate limit is "
                        "25 requests per day."
                    )
                }

        return Resp()

    monkeypatch.setattr(
        "alphaedge.modules.market_data.infrastructure.quotes.settings.alpha_vantage_api_key",
        "test-key",
    )
    import httpx

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        get = fake_get

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kw: FakeClient())

    with pytest.raises(ValidationError, match="25 requests per day"):
        await client.fetch("AAPL")
