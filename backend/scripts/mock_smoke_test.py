#!/usr/bin/env python3
"""End-to-end mock mode smoke test — no Docker, no external API keys."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.services import BarNormalizer, BarValidator
from alphaedge.modules.market_data.infrastructure.providers import (
    MockMarketDataProvider,
    get_provider,
)


def test_provider_registry() -> None:
    mock = get_provider("mock")
    assert mock.name == "mock"
    print("✓ Provider registry: mock available")


async def test_mock_fetch_and_validate() -> None:
    provider = MockMarketDataProvider()
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 7, 1, tzinfo=UTC)
    symbols = ["AAPL", "MSFT", "GOOGL"]

    total_bars = 0
    for symbol in symbols:
        raw_bars = await provider.fetch_bars(symbol, Timeframe.D1, start, end)
        assert raw_bars, f"No bars returned for {symbol}"
        for raw in raw_bars:
            BarValidator.validate(raw)
        total_bars += len(raw_bars)
        first, last = raw_bars[0], raw_bars[-1]
        print(
            f"✓ {symbol}: {len(raw_bars)} daily bars "
            f"({first.timestamp.date()} → {last.timestamp.date()}, close={last.close})"
        )

    print(f"✓ Mock ingestion simulation: {total_bars} bars validated across {len(symbols)} symbols")


def test_normalization() -> None:
    from uuid import uuid4

    provider = MockMarketDataProvider()
    raw = asyncio.run(
        provider.fetch_bars(
            "SPY",
            Timeframe.D1,
            datetime(2026, 6, 1, tzinfo=UTC),
            datetime(2026, 6, 5, tzinfo=UTC),
        )
    )[0]
    instrument_id = uuid4()
    bar = BarNormalizer.to_domain(raw, instrument_id, Timeframe.D1, "mock")
    assert bar.instrument_id == instrument_id
    assert bar.source == "mock"
    assert bar.open > Decimal("0")
    print(f"✓ Normalization: SPY bar → domain entity (close={bar.close})")


async def test_api_liveness() -> None:
    from httpx import ASGITransport, AsyncClient

    from alphaedge.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        live = await client.get("/api/v1/health/live")
        assert live.status_code == 200
        assert live.json()["status"] == "ok"
        print("✓ API liveness: /health/live OK")

        docs = await client.get("/api/v1/openapi.json")
        assert docs.status_code == 200
        paths = docs.json().get("paths", {})
        expected = [
            "/api/v1/auth/register",
            "/api/v1/instruments",
            "/api/v1/market-data/ingest",
            "/api/v1/strategies",
            "/api/v1/backtest-runs",
            "/api/v1/indicators",
        ]
        for path in expected:
            assert path in paths, f"Missing route: {path}"
        print(f"✓ OpenAPI: {len(paths)} routes documented (auth + market data present)")


def main() -> int:
    print("AlphaEdge Mock Mode Smoke Test")
    print("=" * 40)
    try:
        test_provider_registry()
        asyncio.run(test_mock_fetch_and_validate())
        test_normalization()
        asyncio.run(test_api_liveness())
    except Exception as exc:
        print(f"\n✗ FAILED: {exc}")
        return 1

    print("=" * 40)
    print("All mock-mode checks passed.")
    print("\nNote: Full API flow (auth, DB ingest, bar storage) requires")
    print("Postgres + Redis. Start Docker with `make dev` or install them locally.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
