# Changelog

All notable changes to AlphaEdge are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versions follow [Semantic Versioning](https://semver.org/).

---

---

## [1.1.0] — 2026-07-14

### Added
- WebSocket order status updates (`/api/v1/ws/orders`) with Redis pub/sub
- Market data WebSocket fan-out via Redis instead of DB polling
- Deployments management page with pause/resume
- Risk snapshot Redis cache and daily Celery beat schedule
- Grafana Prometheus datasource auto-provisioning
- OAuth tokens in HTTP-only cookies
- Deployment bar-to-signal-to-order integration test
- Validation error line numbers in strategy editor

### Fixed
- Alpaca orders now send instrument symbol instead of UUID prefix
- `orders_submitted_total` and DB query latency metrics wired

## [1.0.0] — 2026-07-11

### Summary
First production-ready release of AlphaEdge. This version encompasses all work from Phase 0 (architecture planning) through Phase 14 (release candidate polish), delivering a full-featured quantitative trading research and execution platform.

### Added — Phase 14 (Release Candidate Polish)
- **Pre-trade risk gate** (`RiskGate`) enforced on every order submission and strategy deployment signal
- `RiskLimitType.MAX_PORTFOLIO_EXPOSURE_PCT` and `DAILY_LOSS_PCT` limit types
- `RiskRejectedError` with `RISK_REJECTED` code and `stage` context in API responses
- Shared Prometheus metrics module (`shared/infrastructure/metrics.py`) with HTTP, Celery, WebSocket, risk, DB, and order counters
- `main.py` wired to shared metrics; structlog `request_id` bound per request via `contextvars`; unhandled exceptions logged with full context
- Celery task signals (`task_prerun`, `task_success`, `task_failure`) incrementing `CELERY_TASKS` / `CELERY_TASK_LATENCY` and binding `task_id` to log context
- WebSocket handler tracks `WS_CONNECTIONS` gauge and `WS_MESSAGES` counter per direction
- Grafana dashboard expanded with panels for risk rejections, Celery throughput/latency, and WebSocket connections/messages
- Prometheus + Grafana services in `infrastructure/docker-compose.yml` under optional `observability` profile
- `infrastructure/prometheus.yml` scrape config targeting the API metrics endpoint
- `backend/tests/unit/test_risk_gate.py` — 8 unit tests covering all gate stages
- `backend/tests/integration/test_strategy_deployment.py` — CRUD integration tests for deployment lifecycle
- `backend/tests/unit/test_portfolio_risk.py` — expanded with `MAX_POSITION_PCT` LimitEnforcer test
- `frontend/e2e/auth.spec.ts`, `marketplace.spec.ts`, `strategy-authoring.spec.ts` Playwright smoke tests
- Makefile `setup`, `check`, `frontend-lint`, `ci-local` targets
- `.env.example` fully documented with inline guidance for every variable
- `scripts/validate_env.py` — validate environment variables before startup
- `docs/CI.md`, `docs/DEPLOYMENT.md`, `docs/RISK_MODEL.md`, `docs/TROUBLESHOOTING.md`, `docs/LOCAL_DEVELOPMENT.md`
- `docs/RELEASE_CHECKLIST.md`, `docs/PRODUCTION_CHECKLIST.md`
- `docs/PERFORMANCE.md` with baseline notes and known N+1 risks
- `CHANGELOG.md`, `RELEASE_NOTES.md`
- Phase 14 marked complete in `docs/ROADMAP.md`
- Phase 14 addendum in `docs/security/SECURITY_AUDIT.md`

### Changed — Phase 14
- `main.py` now imports metrics from `shared.infrastructure.metrics` (no local Counter/Histogram definitions)
- `backend-ci.yml` pip-audit step filters editable/local packages from requirements to prevent false positives
- `backend-ci.yml` and `frontend-ci.yml` bump `actions/checkout` to v5
- `pyproject.toml` version bumped to `1.0.0`
- `frontend/package.json` version bumped to `1.0.0`
- `FastAPI` app title version updated to `1.0.0`

---

## [0.14.0-rc.1] — Phase 13 (Insights, Performance, Security Hardening)

### Added
- AI-powered strategy insights via OpenAI integration
- Login lockout and brute-force protection (`shared/infrastructure/login_lockout.py`)
- Rate limiting with Redis sliding window, configurable per tier
- C++ vectorised backtest engine (`backend/cpp/`)
- Strategy optimization (grid search / Optuna) via Celery
- Marketplace with public strategy listings, cloning, and ratings
- Organization / multi-user workspace support
- OAuth login (Google, GitHub) with PKCE state in Redis
- API key authentication for programmatic access
- Collaboration (comments, annotations on strategies/backtests)
- Risk module: RiskSnapshot, RiskLimit, LimitEnforcer, per-portfolio exposure tracking
- Portfolio rebalancer and performance calculator
- Live trading toggle with Alpaca broker adapter
- WebSocket market data streaming endpoint
- Structured logging with structlog + JSON output
- Prometheus metrics endpoint (request count, latency)
- GitHub Actions CI for backend (lint, type check, coverage) and frontend (lint, audit, build)
- Full e2e test suite with Playwright (`user-journey.spec.ts`)
- k8s manifests and Terraform AWS skeleton in `infrastructure/`

---

## [0.1.0] — Phases 0–12 (Foundation through Strategy Execution)

### Added (highlights)
- **Phase 0** — Architecture, database schema, API design, repository structure
- **Phase 1** — Identity module (register, login, JWT, refresh, RBAC), health checks
- **Phase 2** — Strategy module (DSL compiler, Python runtime, versioning, validation)
- **Phase 3** — Market data ingestion (bars, instruments, Polygon/Alpha Vantage adapters)
- **Phase 4** — Backtesting engine (event-driven simulator, equity curve, metrics)
- **Phase 5** — Execution module (orders, broker connections, paper broker, Alpaca adapter)
- **Phase 6** — Portfolio module (holdings, cash tracking, paper P&L)
- **Phase 7** — Strategy deployments (attach strategy to paper broker, bar → signal → order loop)
- **Phase 8** — Risk module (risk limits, snapshots, VaR, drawdown, Sharpe)
- **Phase 9** — Optimization (Celery-parallel grid search, Optuna integration)
- **Phase 10** — Marketplace (publish, discover, clone strategies; ratings)
- **Phase 11** — Organizations and collaboration
- **Phase 12** — AI insights, security hardening, performance tuning

[1.0.0]: https://github.com/your-org/alpha-edge/compare/v0.14.0-rc.1...v1.0.0
[0.14.0-rc.1]: https://github.com/your-org/alpha-edge/compare/v0.1.0...v0.14.0-rc.1
[0.1.0]: https://github.com/your-org/alpha-edge/releases/tag/v0.1.0
