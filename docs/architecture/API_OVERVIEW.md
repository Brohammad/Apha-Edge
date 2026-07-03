# AlphaEdge — API Design Overview

## 1. Conventions

| Aspect | Standard |
|--------|----------|
| Base URL | `https://api.alphaedge.io/api/v1` |
| Format | JSON (`Content-Type: application/json`) |
| Auth | Bearer JWT or `X-API-Key` header |
| Versioning | URL path prefix (`/api/v1/`) |
| Pagination | Cursor-based: `?cursor=<token>&limit=50` |
| Sorting | `?sort=-created_at` (prefix `-` for descending) |
| Filtering | `?status=completed&strategy_id=<uuid>` |
| Idempotency | `Idempotency-Key` header on POST |
| Errors | RFC 7807 Problem Details envelope |
| Documentation | Auto-generated OpenAPI 3.1 at `/api/v1/docs` |

### Response Envelope

```json
{
  "data": { ... },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-07-02T12:00:00Z"
  }
}
```

### Paginated Response

```json
{
  "data": [ ... ],
  "meta": {
    "cursor": "eyJpZCI6IjU1MGU4...",
    "has_more": true,
    "total_count": 142
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "BACKTEST_NOT_FOUND",
    "message": "Backtest run not found",
    "details": { "backtest_run_id": "550e8400-..." },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## 2. Authentication Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Email/password login → JWT |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/oauth/{provider}` | Initiate OAuth flow |
| GET | `/auth/oauth/{provider}/callback` | OAuth callback |
| GET | `/auth/me` | Current user profile |
| POST | `/auth/api-keys` | Create API key |
| GET | `/auth/api-keys` | List API keys |
| DELETE | `/auth/api-keys/{id}` | Revoke API key |

---

## 3. Module Endpoints

### 3.1 Market Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/instruments` | List/search instruments |
| GET | `/instruments/{id}` | Get instrument details |
| POST | `/instruments` | Register instrument (admin) |
| GET | `/instruments/{id}/bars` | Get OHLCV bars |
| GET | `/instruments/{id}/bars/latest` | Latest bar |
| POST | `/market-data/ingest` | Trigger ingestion job |
| GET | `/market-data/ingest/{job_id}` | Ingestion job status |
| WS | `/ws/market-data/{instrument_id}` | Live bar/tick stream |

### 3.2 Strategy

| Method | Path | Description |
|--------|------|-------------|
| GET | `/strategies` | List user strategies |
| POST | `/strategies` | Create strategy |
| GET | `/strategies/{id}` | Get strategy |
| PUT | `/strategies/{id}` | Update strategy metadata |
| DELETE | `/strategies/{id}` | Soft delete strategy |
| POST | `/strategies/{id}/versions` | Create new version |
| GET | `/strategies/{id}/versions` | List versions |
| GET | `/strategies/{id}/versions/{vid}` | Get version source |
| POST | `/strategies/{id}/versions/{vid}/validate` | Validate/compile strategy |
| GET | `/indicators` | List available indicators |

### 3.2b Strategy deployments (paper)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/strategy-deployments` | List deployments |
| POST | `/strategy-deployments` | Deploy validated version to paper |
| POST | `/strategy-deployments/{id}/pause` | Pause signal evaluation |
| POST | `/strategy-deployments/{id}/resume` | Resume deployment |

Requires validated `strategy_version_id`, paper `broker_connection_id`, and `portfolio_id`. Signals are evaluated when bars are ingested. See [STRATEGY_GUIDE.md](../STRATEGY_GUIDE.md).

### 3.3 Backtesting

| Method | Path | Description |
|--------|------|-------------|
| POST | `/backtest-runs` | Submit backtest job (`config.allow_short` optional) |
| GET | `/backtest-runs` | List backtest runs |
| GET | `/backtest-runs/{id}` | Get run status + config |
| GET | `/backtest-runs/{id}/result` | Get result metrics |
| GET | `/backtest-runs/{id}/trades` | Get trade list |
| GET | `/backtest-runs/{id}/equity-curve` | Get equity curve data |
| DELETE | `/backtest-runs/{id}` | Cancel/delete run |

### 3.4 Portfolio

| Method | Path | Description |
|--------|------|-------------|
| GET | `/portfolios` | List portfolios |
| POST | `/portfolios` | Create portfolio |
| GET | `/portfolios/{id}` | Get portfolio details |
| GET | `/portfolios/{id}/holdings` | Current holdings |
| GET | `/portfolios/{id}/performance` | Performance summary |
| POST | `/portfolios/{id}/rebalance` | Generate rebalance plan |
| GET | `/portfolios/{id}/rebalance/{plan_id}` | Get rebalance plan |

### 3.5 Risk

| Method | Path | Description |
|--------|------|-------------|
| POST | `/portfolios/{id}/risk/compute` | Trigger risk computation |
| GET | `/portfolios/{id}/risk/snapshots` | List risk snapshots |
| GET | `/portfolios/{id}/risk/snapshots/latest` | Latest snapshot |
| GET | `/portfolios/{id}/risk/limits` | Get risk limits |
| PUT | `/portfolios/{id}/risk/limits` | Update risk limits |

### 3.6 Optimization

| Method | Path | Description |
|--------|------|-------------|
| POST | `/optimization-runs` | Submit optimization job |
| GET | `/optimization-runs` | List optimization runs |
| GET | `/optimization-runs/{id}` | Get run status |
| GET | `/optimization-runs/{id}/trials` | List trials with results |
| GET | `/optimization-runs/{id}/best` | Best trial result |

### 3.7 Execution

| Method | Path | Description |
|--------|------|-------------|
| GET | `/broker-connections` | List broker connections |
| POST | `/broker-connections` | Add broker connection |
| DELETE | `/broker-connections/{id}` | Remove connection |
| POST | `/orders` | Submit order |
| GET | `/orders` | List orders |
| GET | `/orders/{id}` | Get order details |
| DELETE | `/orders/{id}` | Cancel order |
| GET | `/orders/{id}/executions` | Get fills |

### 3.8 AI Insights

| Method | Path | Description |
|--------|------|-------------|
| POST | `/insights` | Request insight generation |
| GET | `/insights` | List insight requests |
| GET | `/insights/{id}` | Get insight report |
| POST | `/insights/strategy-explain` | Explain a strategy |
| POST | `/insights/performance-report` | Generate performance report |

---

## 4. WebSocket Protocol

**Connection:** `wss://api.alphaedge.io/ws/v1/market-data`

```json
// Subscribe
{ "action": "subscribe", "channels": ["bars:AAPL:1m", "bars:MSFT:1d"] }

// Unsubscribe
{ "action": "unsubscribe", "channels": ["bars:AAPL:1m"] }

// Incoming bar
{
  "channel": "bars:AAPL:1m",
  "data": {
    "timestamp": "2026-07-02T15:30:00Z",
    "open": 190.50, "high": 191.00, "low": 190.30, "close": 190.85,
    "volume": 125000
  }
}
```

---

## 5. Rate Limiting

| Tier | Requests/min | Backtest jobs/hour |
|------|-------------|-------------------|
| Free | 60 | 5 |
| Pro | 600 | 50 |
| Enterprise | Custom | Custom |

Headers returned:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1719928800
```

---

## 6. Health & Observability Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness (DB, Redis, workers) |
| GET | `/metrics` | Prometheus metrics (internal) |
