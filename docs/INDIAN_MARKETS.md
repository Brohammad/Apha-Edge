# Indian Markets — AlphaEdge

AlphaEdge supports NSE and BSE equities with INR-denominated instruments, Indian trading calendars, and broker adapters for Zerodha, Angel One, and Upstox.

## Exchanges

| Exchange | Code | Session (IST) | Currency |
|----------|------|---------------|----------|
| National Stock Exchange | `NSE` | 09:15 – 15:30 | INR |
| Bombay Stock Exchange | `BSE` | 09:15 – 15:30 | INR |

Pre-open session runs 09:00 – 09:15 IST on both exchanges.

## Product Types

Indian brokers use product types that map to AlphaEdge `ProductType`:

| Product | Description |
|---------|-------------|
| `CNC` | Cash and carry — delivery equity |
| `MIS` | Intraday margin product — squared off same day |
| `NRML` | Normal margin — overnight F&O positions |

## Exchange Segments

`ExchangeSegment` identifies the routing segment:

- `NSE_EQ`, `NSE_FO` — NSE cash and F&O
- `BSE_EQ`, `BSE_FO` — BSE cash and F&O

## Seeded Instruments

Run `python backend/scripts/seed_data.py` to load sample NSE/BSE symbols:

- `RELIANCE` (NSE)
- `TCS` (NSE)
- `INFY` (NSE)
- `HDFCBANK` (NSE)
- `SBIN` (BSE)

## Trading Calendar

`TradingCalendar` in `market_data.domain.trading_calendar` exposes:

- `is_market_open(exchange, at)` — session check with holidays
- `is_trading_day(exchange, date)` — weekday + holiday filter
- `next_open(exchange, after)` — next session open in UTC

## Broker Adapters

Configure credentials per broker in `.env` and connect via **Settings → Broker Connections**:

| Broker | Env keys | Notes |
|--------|----------|-------|
| Zerodha | `ZERODHA_API_KEY`, `ZERODHA_API_SECRET` | Kite Connect OAuth |
| Angel One | `ANGELONE_API_KEY`, `ANGELONE_CLIENT_CODE` | SmartAPI |
| Upstox | `UPSTOX_API_KEY`, `UPSTOX_API_SECRET` | OAuth 2.0 |

See [BROKERS.md](./BROKERS.md) for connection flow.

## Market Data

Historical bars for Indian symbols use the `indian` provider (`INDIAN_MARKET_DATA_PROVIDER=mock` by default). Option chain snapshots are available at `GET /api/v1/market-data/options/{symbol}/chain`.

## Risk — MIS Margin

The risk gate estimates MIS margin at ~20% of notional for intraday equity orders. Configure portfolio limits as usual via `/api/v1/risk/limits`.
