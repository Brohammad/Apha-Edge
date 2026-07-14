# AlphaEdge v1.1.0 — Release Notes

**Release date:** 2026-07-14

## Highlights

- **Live order blotter** — WebSocket push updates when paper/live orders fill
- **Deployments dashboard** — list, pause, and resume strategy deployments
- **OAuth security** — access and refresh tokens in HTTP-only cookies (no URL tokens)
- **Observability** — Grafana auto-provisions Prometheus; risk snapshots cached in Redis
- **Execution fix** — Alpaca orders use correct ticker symbols

## Upgrade

1. Pull latest code and run `make migrate`
2. Restart API, worker, and Celery beat (if enabled)
3. Re-login to refresh cookie-based session

No breaking API changes for authenticated REST clients using cookies or Bearer tokens.
