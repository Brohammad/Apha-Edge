# AlphaEdge v1.0 Engineering Audit

**Date:** 2026-07-14  
**Scope:** Final hardening pass before public v1.0 release  
**Version audited:** 1.1.0

This document is the consolidated deliverable for the v1.0 engineering polish pass. It covers repository audit, documentation consistency, performance, security, architecture review, technical debt, and a suggested v1.1 roadmap grounded in engineering needs.

---

## 1. Repository Audit Report (Phase A)

### Structure

AlphaEdge is a **modular monolith**: FastAPI API + Celery workers + React 19 frontend, with optional mobile companion and C++ backtest accelerator (`backend/cpp/`).

Nineteen bounded contexts under `backend/src/alphaedge/modules/`. Production-ready paths: identity, market_data, strategy, backtesting, optimization, portfolio, risk, execution, insights, marketplace, organization, collaboration. Scaffold or partial: events (outbox dispatcher without producers), sec (skeleton task), deployment (unwired live-deploy helpers), analytics (demo SQL).

### Dead code removed in this pass

| Item | Reason |
|------|--------|
| `cpp/` (root CMake RSI stub) | Superseded by `backend/cpp/` |
| `observability/` | Orphan; compose uses `infrastructure/grafana/` |
| `modules/options/` | No imports; options not in scope |
| `shared/application/bus.py` | Unused CommandHandler/EventBus abstractions |
| `shared/application/unit_of_work.py` | Unused UnitOfWork ABC |
| Strategy `/templates` route ordering | Fixed — was shadowed by `/{strategy_id}` |

### Remaining dead code (documented, not removed)

~20 domain files with zero callers (marketplace search/leaderboard, collaboration presence, backtesting monte_carlo/vectorized, risk kill_switch/liquidity/concentration, etc.). Kept to avoid large churn; listed in §6 Technical Debt.

### Other findings

- **Unreachable routes:** None after template fix.
- **Unused frontend:** `WalkForwardChart.tsx`, `BrokerConnectionModal.tsx`, `/live-chart` route — API exists but UI not wired.
- **Stub brokers:** IBKR, Zerodha, Angel One, Upstox, Binance, Coinbase registered but raise `BrokerError` on submit.
- **Outbox:** `store_outbox_event()` never called; dispatcher runs on empty table.
- **DTO duplication:** Entity → application DTO → presentation Response → manual `_to_*` mappers across all modules (~40% presentation boilerplate).

---

## 2. Documentation Consistency Report (Phase B)

### Fixes applied

| Document | Change |
|----------|--------|
| `README.md` | Capability matrix; cookie + Bearer auth; rate-limit cookie gap; v1.1 status |
| `docs/security/SECURITY_AUDIT.md` | Phase 15 addendum — cookies, OAuth fix, WS tickets, Fernet encryption |
| `docs/architecture/API_OVERVIEW.md` | Offset pagination, error envelope, WebSocket paths, idempotency body |
| `docs/architecture/ARCHITECTURE.md` | Implementation status v1.1; broker honesty; outbox/OTEL limitations |
| `docs/STRATEGY_GUIDE.md` | Python sandbox trust model; HOLD backtest vs deployment behavior |
| `docs/RISK_MODEL.md` | MIS margin in cash_availability stage |
| `docs/CI.md` | mypy documented as local-only; CI runs ruff + pytest only |
| `.env.example` | Removed stale `ANGELONE_CLIENT_CODE` |

### Known doc vs code gaps (honest limitations)

| Topic | Reality |
|-------|---------|
| ROADMAP Phases 29–30 | Marked complete but live broker deployments and marketplace subscriptions/leaderboards are not API-wired |
| RBAC | `require_permission()` exists but routes use ownership checks only |
| Kill switch | ROADMAP Phase 25 complete; no implementation in `RiskGate` |
| OpenTelemetry | `otel_enabled=false` by default; console exporter only |
| Readiness probe | Checks Postgres + Redis only, not Celery workers |
| Anthropic | Not implemented; only OpenAI + mock |

---

## 3. Performance Findings (Phase F)

Static analysis and architecture review (no production profiling run in this pass):

| Area | Finding | Severity |
|------|---------|----------|
| Order listing | Offset pagination with `COUNT(*)` on large tables | Medium — cursor pagination deferred |
| Backtest engine | Python path replays bars in-process; C++ optional for DSL crossover only | Low — acceptable for research |
| Strategy runtime | Module-global `_RUNTIME_CACHE` per deployment | Low — fine for single-tenant |
| Market data ingestion | `evaluate_deployments_for_bar` synchronous per bar in ingestion worker | Medium — blocks ingestion on many deployments |
| Portfolio risk | Daily Celery snapshot + Redis cache for gate | Low — appropriate |
| N+1 queries | Some list endpoints load relations in loops | Medium — audit per hot path in v1.1 |
| Serialization | Duplicate DTO→Response mapping adds CPU on large lists | Low |

**Recommendation:** Profile `evaluate_deployments_for_bar` and order list endpoints under load before v1.1; defer micro-optimizations elsewhere.

---

## 4. Security Findings (Phase I)

### Strengths

- JWT HS256 + refresh token rotation (hashed in DB)
- HTTP-only cookies for web SPA (`alphaedge_access` / `alphaedge_refresh`)
- OAuth PKCE-style state in Redis; tokens not in redirect URL (v1.1)
- Broker credentials Fernet-encrypted when `CREDENTIALS_ENCRYPTION_KEY` set
- WebSocket production auth via single-use Redis tickets
- Metrics endpoint gated in production (`X-Metrics-Key` or admin JWT)
- Login lockout, rate limiting, security headers, password policy + HIBP
- Idempotency keys on orders (DB unique constraint)

### Gaps

| Issue | Risk | Mitigation |
|-------|------|------------|
| Python strategy `exec()` | High in multi-tenant | Document trusted-environment only; AST + restricted builtins (no `__import__`) |
| RBAC not enforced on routes | Medium | Ownership checks sufficient for single-user; wire RBAC for org features |
| Rate limit tier from Bearer only | Low | Cookie-only web users get IP-based anonymous tier |
| No log PII scrubbing | Low | Structlog; no email in logs today |
| Stale bar prices in risk gate | Operational | Documented limitation for paper/research |

---

## 5. Architecture Review (Phase M)

### What works well

- Clear bounded-context folder structure (domain → application → infrastructure → presentation)
- Risk gate as single enforcement point for manual and deployment orders
- Celery for long-running work; FastAPI for sync API
- Honest separation of paper vs live trading guards
- Prometheus metrics wired across HTTP, Celery, WebSocket, risk

### Smells (no refactor in v1.0)

| Smell | Location | Notes |
|-------|----------|-------|
| God router handlers | organization, marketplace, analytics | Inline dict assembly, no application layer |
| DTO/Response duplication | All modules | Consistency tax, not a bug |
| Dormant abstractions | events/outbox, deployment/live_deploy | Half-implemented patterns |
| In-process strategy cache | `strategy/domain/runtime.py` | Not process-isolated |
| Generic Celery retry | `execution/infrastructure/tasks.py` | Retries permanent failures up to max_retries |

### Dependency direction

Generally correct: presentation → application → domain; infrastructure implements domain ports. Analytics and organization routers bypass application layer — inconsistent but functional.

---

## 6. Technical Debt List

### P0 (before multi-tenant or live auto-trading)

1. Python strategy isolation — container/Firecracker or hosted sandbox (v1.1+)
2. Wire RBAC or document ownership-only authorization model
3. Market-hours and quote freshness checks in execution path
4. Outbox producers or remove outbox infrastructure

### P1 (maintainability)

5. Consolidate DTO + Response schemas
6. Remove or wire ~20 dead domain modules
7. Wire `WalkForwardChart` or remove; fix marketplace subscription/leaderboard routes or remove domain code
8. Add Playwright + Docker build to CI (or remove stale doc references)
9. Frontend TypeScript `strict: true`
10. Cursor pagination for high-volume list endpoints

### P2 (nice to have)

11. Remove stub brokers from registry until implemented
12. Kill switch in risk gate
13. Jaeger/Tempo exporter for OpenTelemetry
14. Celery worker health in readiness probe
15. `Idempotency-Key` HTTP header support (body field works today)

---

## 7. Suggested v1.1 Roadmap (Engineering-Driven)

| Item | Rationale |
|------|-----------|
- **CI completeness** | Enable mypy in CI after clearing strict-mode backlog; Playwright smoke in CI; Docker image build gate |
| **Strategy sandbox** | Process isolation or documented hosted runner for untrusted code |
| **Execution hardening** | Market calendar, stale quote rejection, live-trading integration tests |
| **Outbox or simplify** | Either wire event producers or delete half-implemented outbox |
| **Schema consolidation** | Reduce DTO duplication — measurable maintainer velocity gain |
| **RBAC enforcement** | Required before org-level features go production |
| **Performance profiling** | Deployment bar evaluation and order listing under load |
| **Indian broker adapters** | Only when execution path is hardened — stubs exist today |

**Explicitly not v1.1:** options, crypto, new AI providers, new optimization algorithms, new marketplace product features.

---

## Phase summaries (C–L)

### C — CI Truthfulness

- Relaxed mypy from fake `strict = true` to honest gradual typing (`strict = false`)
- mypy remains local-only via `make lint-types` until backlog cleared
- Playwright and Docker build remain local-only (documented)

### D — Python Strategy Runtime

- Removed `__import__` from restricted builtins
- Documented trusted-environment-only model in STRATEGY_GUIDE
- Added unit tests for blocked calls and dangerous imports

### E — Execution Engine

- Idempotency, risk gate ordering, Celery retries verified
- Gaps: no market-hours check, no stale quote rejection, partial fills not enabled in registry
- Added paper broker partial-fill unit test

### G — Frontend

- Route-level lazy loading not introduced (bundle acceptable for v1.0)
- Unused components documented; no UI redesign

### H — API Consistency

- OpenAPI auto-generated; API_OVERVIEW aligned with offset pagination and error envelope
- Idempotency via JSON body `idempotency_key`, not header

### J — Developer Experience

- Makefile `check`/`ci-local` aligned with CI
- `.env.example` cleaned

### K — Release Engineering

- CHANGELOG and RELEASE_NOTES accurate for v1.1.0
- Capability matrix in README
- Version 1.1.0 consistent across pyproject.toml, package.json, main.py

### L — Capability Matrix

See [README.md](../README.md#capability-matrix).

---

*Audit performed as final engineering pass. No new product features added.*
