# AlphaEdge Security Audit — Phase 10

**Date:** 2026-07-03  
**Scope:** Backend API, authentication, execution layer, deployment configuration

## Summary

| Area | Status | Notes |
|------|--------|-------|
| Authentication | Pass | JWT + refresh rotation; OAuth state in Redis |
| Authorization | Pass | RBAC on domain entities |
| API keys | Pass | SHA-256 hashed, prefix-only display, revocable |
| Rate limiting | Pass | Redis sliding window per tier |
| Input validation | Pass | Pydantic at API boundary |
| SQL injection | Pass | SQLAlchemy parameterized queries |
| Secrets | Pass | Environment variables; AWS Secrets Manager in prod |
| CORS | Pass | Configurable per environment |
| WebSocket auth | Pass | Production: single-use Redis ticket via `Sec-WebSocket-Protocol`. Dev: JWT query param. |
| Broker credentials | Pass | Fernet encryption when `CREDENTIALS_ENCRYPTION_KEY` set; required for live trading |

## Findings

### Low — OAuth redirect tokens in query string

**Resolved in v1.1.0.** OAuth callback sets HTTP-only cookies and redirects with `?oauth=success` only. Tokens are not passed in the URL.

### Low — Alpaca fallback simulation

When Alpaca API returns errors, orders fall back to local paper simulation. Log and alert in production to avoid silent mode confusion.

### Informational — Rate limit bypass for health/metrics

Health and metrics endpoints are exempt from application rate limits. Nginx layer still applies `limit_req`.

## Recommendations (Phase 11+)

1. Encrypt broker credentials and OAuth tokens at rest (KMS envelope encryption)
2. Add CSP headers via Nginx
3. Enable WAF on ALB
4. Periodic dependency scanning (`pip-audit`, Dependabot)
5. Penetration test before live trading

## Checklist

- [x] No secrets in repository
- [x] Passwords bcrypt-hashed
- [x] Refresh tokens hashed in DB
- [x] API keys never stored in plaintext
- [x] Domain errors do not leak stack traces
- [x] Idempotency keys on order submission
- [x] Audit log table for mutating operations

---

## Phase 14 Addendum — 2026-07-11

**Scope:** Risk gate enforcement, observability, unhandled exception logging.

### Changes reviewed

| Area | Verdict | Notes |
|------|---------|-------|
| CSRF | Mitigated | Web SPA uses HTTP-only cookies with `SameSite=Lax`. State-changing API calls from the SPA use cookies + CORS; programmatic clients use Bearer/API key (not CSRF-exposed). |
| Pre-trade risk gate | Pass | `RiskGate.evaluate` runs on every order before persisting. Six pipeline stages covering cash, position sizing, exposure, and loss limits. Rejected orders return `RISK_REJECTED` without leaking internal details beyond the stage name. |
| Login lockout | Pass | `login_lockout.py` blocks repeated failed login attempts using a Redis counter with TTL. |
| Unhandled exceptions | Pass | `unhandled_exception_handler` logs the exception type and path via structlog but returns only `"An unexpected error occurred"` to the client — no stack trace or internal detail exposed in production. |
| Metrics endpoint | Pass | `/api/v1/metrics` requires either `X-Metrics-Key` header or admin-role JWT in production. Unauthenticated access returns `401`. |
| Structlog contextvars | Pass | `request_id` is bound per request and cleared before each new request. No cross-request contamination. |
| Celery signal handlers | Pass | Import from `shared.infrastructure.metrics` only; no user data in metric labels. |

### No new vulnerabilities identified in Phase 14.

### Recommendations (Phase 15+)

1. Add Content-Security-Policy reporting (`report-uri` / `report-to`) to track injection attempts in production.
2. ~~Evaluate HTTP-only cookie flow for OAuth tokens~~ — **Done in v1.1.0**
3. Add WAF on ALB before production live trading at scale.
4. Schedule quarterly `pip-audit` and `npm audit` runs via Dependabot or a scheduled CI job.

---

## Phase 15 Addendum — 2026-07-14 (v1.0 hardening)

**Scope:** Cookie auth, Python strategy trust model, CI truthfulness, documentation alignment.

### Changes reviewed

| Area | Verdict | Notes |
|------|---------|-------|
| Cookie authentication | Pass | `alphaedge_access` / `alphaedge_refresh` HTTP-only; `get_auth_context` reads Bearer or cookie |
| OAuth cookies | Pass | Callback sets cookies; no tokens in redirect URL |
| Python strategy runtime | Informational | AST + restricted builtins; `exec()` in-process — **trusted environments only**; not multi-tenant safe |
| mypy | Informational | Gradual typing (`strict = false`); not CI-gated until backlog cleared |
| RBAC on routes | Informational | `require_permission()` defined but unused; ownership checks enforce access today |
| Rate limit + cookies | Informational | Tier resolution uses Bearer/API key; cookie-only sessions use IP-based anonymous tier |

### Recommendations (v1.1+)

1. Process-isolated strategy execution before marketplace untrusted code
2. Wire RBAC or document ownership-only authorization explicitly
3. Market-hours and quote freshness checks in execution path
4. Wire outbox producers or remove unused outbox infrastructure
