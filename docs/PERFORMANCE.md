# Performance Notes

Baseline observations, known bottlenecks, and optimisation opportunities for AlphaEdge v1.0.0.

---

## Baseline measurements

These figures are from a local development machine (M3 MacBook Pro, Docker Compose stack).

| Operation | Typical latency | Notes |
|-----------|----------------|-------|
| `POST /api/v1/auth/login` | ~40 ms | bcrypt hash comparison dominates |
| `GET /api/v1/strategies` | ~8 ms | Simple SELECT with user filter |
| `POST /api/v1/backtests` (queued) | ~10 ms | Returns immediately; task runs async |
| Backtest task (1 year, 1 symbol, DSL) | ~0.2 s | Pure Python engine |
| Backtest task (1 year, 1 symbol, C++ engine) | ~0.02 s | 10× speedup via `alphaedge-cpp` |
| `POST /api/v1/orders` (with risk gate, bar lookup) | ~25 ms | Includes 2 DB reads (holdings, limits) |
| `GET /api/v1/orders` (single portfolio, 100 orders) | ~12 ms | |
| `GET /api/v1/orders` (all portfolios, no filter) | ~80–400 ms | **N+1 — see below** |

---

## Known N+1 query risks

### `ListOrdersHandler` without portfolio filter

**Location:** `backend/src/alphaedge/modules/execution/application/handlers.py`, `ListOrdersHandler.handle`

**Status (v1.0):** Fixed. Cross-portfolio listing uses a single `list_by_portfolio_ids` query (`WHERE portfolio_id IN (...)`) instead of one query per portfolio.

**Still recommended:** Pass `portfolio_id` when the blotter is scoped to one book, so pagination totals stay exact.

### `RiskSnapshotRepository` — latest snapshot lookup

**Location:** `SubmitOrderHandler._enforce_risk_gate`

**Issue:** Each order submission fetches the latest risk snapshot via a `SELECT ... ORDER BY snapshot_at DESC LIMIT 1`. This is fast with a B-tree index on `(portfolio_id, snapshot_at DESC)` but should be verified in production at scale.

**Mitigation:** Index exists in the Alembic migration. Cache the snapshot in Redis for high-frequency order flows (e.g. strategy deployments generating many signals per second).

---

## Database indices

The most performance-critical queries are covered by indices:

| Table | Index | Used by |
|-------|-------|---------|
| `orders` | `(portfolio_id, created_at DESC)` | `list_by_portfolio` |
| `orders` | `(idempotency_key)` UNIQUE | `get_by_idempotency_key` |
| `risk_snapshots` | `(portfolio_id, snapshot_at DESC)` | `get_latest` |
| `bars` | `(instrument_id, timeframe, timestamp DESC)` | `get_latest` |
| `strategy_deployments` | `(is_active)`, `instrument_ids` GIN | `list_active_for_instrument` |

Verify index usage in production with `EXPLAIN ANALYZE` on slow queries.

---

## Celery task performance

| Task | Typical duration | Notes |
|------|----------------|-------|
| `execute_backtest` (1yr, DSL) | ~200 ms | Python engine |
| `execute_backtest` (1yr, C++) | ~20 ms | C++ extension required |
| `run_ingestion` (1 instrument, 1yr) | ~2–10 s | Provider-dependent |
| `compute_risk_snapshot` | ~50 ms | Depends on return series length |
| `execute_order` | ~200–2000 ms | Alpaca API round-trip |

Run multiple Celery workers (`--concurrency=4`) to parallelise backtest and ingestion tasks.

---

## WebSocket

The market data WebSocket polls the database every 2 seconds per subscribed instrument. For high-frequency use cases (many connections, many instruments), replace the polling loop with a Redis Pub/Sub fan-out:

1. Publish new bar events to a Redis channel on ingestion.
2. WebSocket handlers subscribe to the relevant channels.
3. Remove the `asyncio.sleep(2)` polling loop.

---

## Profiling

```bash
# Profile the backtest engine
cd backend
python -m cProfile -s cumulative -m pytest tests/unit/test_backtesting.py -k perf > profile.txt

# Check slow queries (development only — Postgres slow query log)
docker compose exec postgres psql -U alphaedge -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

---

## Quick wins for v1.1

1. **Cache risk snapshots in Redis** — 60 s TTL; invalidate on snapshot computation.
2. **WebSocket Redis Pub/Sub** — remove per-connection polling, scale to many connections.
3. **Selectinload on holdings** — wherever holdings and portfolio are loaded separately in the same request, use SQLAlchemy `selectinload` to batch.
