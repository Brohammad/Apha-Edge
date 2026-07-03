import pytest
from decimal import Decimal

from alphaedge.modules.market_data.infrastructure.quotes import (
    AlphaVantageQuoteClient,
    PolygonQuoteClient,
)
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


@pytest.mark.asyncio
async def test_polygon_quote_parses_daily_bars(monkeypatch):
    client = PolygonQuoteClient()

    async def fake_get(*_args, **_kwargs):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "status": "DELAYED",
                    "results": [
                        {"c": 308.63, "t": 1782964800000},
                        {"c": 294.38, "t": 1782878400000},
                    ],
                }

        return Resp()

    monkeypatch.setattr(
        "alphaedge.modules.market_data.infrastructure.quotes.settings.polygon_api_key",
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

    quote = await client.fetch("AAPL")
    assert quote.symbol == "AAPL"
    assert quote.price == pytest.approx(Decimal("308.63"))
    assert quote.source == "polygon"
    assert quote.change_pct is not None
