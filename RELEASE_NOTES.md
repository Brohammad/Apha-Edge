# AlphaEdge v1.0.0 — Release Notes

**Release date:** 2026-07-11  
**Branch:** `phase-14-release-candidate`

---

## What's new in v1.0.0

v1.0.0 marks the first production-ready release of AlphaEdge, a full-stack quantitative trading research and execution platform.

### Highlights

- **Pre-trade risk gate** — every order (manual and deployment-generated) passes through `RiskGate` before persisting. Limits enforced: cash availability, max position %, portfolio exposure %, daily loss %, max drawdown, VaR.
- **Full observability stack** — Prometheus metrics for HTTP, Celery tasks, WebSocket connections, risk rejections, and database query latency. Grafana dashboard included. Start with `docker compose --profile observability up`.
- **Celery task telemetry** — task success/failure counters and per-task latency histograms bound automatically via Celery signals. Task ID is propagated to structlog context for correlation.
- **Structured request context** — `request_id` is bound to structlog `contextvars` for every HTTP request, enabling log correlation across middleware, handlers, and async tasks.
- **DX improvements** — `make setup` bootstraps the project in one command; `make check` runs lint + unit tests; `make ci-local` mirrors CI locally.
- **Documentation** — `docs/LOCAL_DEVELOPMENT.md`, `docs/DEPLOYMENT.md`, `docs/CI.md`, `docs/RISK_MODEL.md`, `docs/TROUBLESHOOTING.md`, `docs/RELEASE_CHECKLIST.md`, `docs/PRODUCTION_CHECKLIST.md`, `docs/PERFORMANCE.md`.

---

## Known limitations

### Risk

- **No real-time price feed in risk gate.** The risk gate uses the most recent daily bar (`D1`) as the estimated fill price. Intraday price gaps are not captured. For production live trading, connect a tick-level data feed.
- **Daily loss limit uses `start_of_day_equity` from the latest `RiskSnapshot`.** If no snapshot has been computed today, it falls back to `portfolio.initial_capital`. Run `compute_risk_snapshot` tasks on a daily schedule.
- **Portfolio exposure % limit** counts all open positions regardless of correlation. A 100% exposure limit does not mean 100% of capital is at risk — it means fully invested.

### Live Trading

- **Live trading is disabled by default.** Set `LIVE_TRADING_ENABLED=true` and complete the production checklist (`docs/PRODUCTION_CHECKLIST.md`) before enabling.
- **Only Alpaca is supported** as a live broker. The paper broker is always available.
- **Order fills are asynchronous.** The API returns an order in `PENDING` status; fills are processed by a Celery worker. There is no real-time fill notification (WebSocket push for order updates is planned for v1.1).

### Strategy Deployments

- **Deployments require a paper broker connection.** Live strategy deployments are not yet supported.
- **Signals are evaluated per bar ingestion.** There is no tick-level signal evaluation. Minimum cadence is 1D bars.

### Market Data

- **Free-tier providers return previous-day close** (Polygon.io free / Alpha Vantage standard). Real-time prices require a paid subscription.
- **Historical data depth varies by provider.** Polygon.io free: up to 2 years. Alpha Vantage: up to 20 years.

### Performance

- **`ListOrdersHandler` without a portfolio filter** previously iterated portfolios (N+1). v1.0 batches via `list_by_portfolio_ids`. Prefer the `portfolio_id` filter for large books anyway.
- **Backtests are single-process per task** (no GPU acceleration). Very large backtests (>10 years, >100 symbols) may take 30–120 seconds.

### Authentication / Security

- **OAuth redirect tokens** are briefly present in the URL query string. The frontend immediately clears them. HTTP-only cookie flow is planned for v1.1.
- **API keys are stored as SHA-256 hashes** with a visible prefix. The full key is shown only once at creation time.

### Infrastructure

- **No multi-region support** in v1.0. The k8s and Terraform skeletons in `infrastructure/` are starting points.
- **Grafana provisioning** requires manual datasource setup (add Prometheus at `http://prometheus:9090`). Automated provisioning is planned for v1.1.

---

## Upgrade notes (from rc.1)

No database migrations are required for Phase 14 changes. The metrics module is additive.

1. Pull the latest code.
2. Re-install the backend: `pip install -e "./backend[dev]"`.
3. Run `python scripts/validate_env.py` to check your `.env`.
4. Restart the API and Celery worker.

---

## Test commands

```bash
# Unit tests (no DB required)
make test-unit

# Integration tests (requires Postgres + Redis)
make test-integration-local

# E2E tests (requires running frontend + API)
make test-e2e

# Frontend e2e only
cd frontend && npx playwright test

# Specific test files
cd backend && pytest tests/unit/test_risk_gate.py -v
cd backend && pytest tests/integration/test_strategy_deployment.py -v -m integration
```
