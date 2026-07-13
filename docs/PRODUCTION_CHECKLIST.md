# Production Checklist

Complete every item on this list before directing real traffic to a new deployment.

## Infrastructure

- [ ] PostgreSQL is on a managed service (RDS, Cloud SQL) with automated backups enabled
- [ ] Redis is on a managed service (ElastiCache, Upstash) with persistence enabled
- [ ] Compute is behind a load balancer with TLS termination
- [ ] Health check configured on load balancer: `GET /api/v1/health/ready`
- [ ] Auto-scaling policy defined (min 2 API replicas for HA)
- [ ] Celery worker replicas ≥ 2

## Secrets

- [ ] `APP_SECRET_KEY` — strong random secret (≥ 32 bytes)
- [ ] `JWT_SECRET_KEY` — strong random secret (≥ 32 bytes), different from APP_SECRET_KEY
- [ ] `CREDENTIALS_ENCRYPTION_KEY` — Fernet key, stored in secrets manager (not in `.env`)
- [ ] No default / placeholder values in production environment
- [ ] Run `python scripts/validate_env.py --prod` — zero errors

## Security

- [ ] `APP_ENV=production` (disables `/api/v1/docs` and `/api/v1/openapi.json`)
- [ ] `APP_DEBUG=false`
- [ ] `TRUST_PROXY_HEADERS=true` (only if behind a trusted proxy like nginx/ALB)
- [ ] CORS origins restricted to the production frontend domain
- [ ] Nginx (or ALB WAF) applying `limit_req` for additional rate limiting
- [ ] `METRICS_API_KEY` set or metrics endpoint IP-restricted at the proxy layer
- [ ] OAuth redirect URLs updated to production domain in Google/GitHub console
- [ ] SSL certificate valid and auto-renewing

## Live trading (if enabling)

- [ ] `LIVE_TRADING_ENABLED=true` — only after all other items on this checklist are done
- [ ] Alpaca API keys are paper keys first — test with paper mode before switching to live
- [ ] Risk limits configured on every live portfolio (see `docs/RISK_MODEL.md`)
- [ ] Daily loss limit set to protect against runaway strategies
- [ ] On-call person designated for trading hours
- [ ] Kill switch tested: set `LIVE_TRADING_ENABLED=false` and verify orders are rejected

## Observability

- [ ] Prometheus scraping the `/api/v1/metrics` endpoint
- [ ] Grafana `AlphaEdge API` dashboard accessible
- [ ] Alerts configured for: error rate > 1%, p95 latency > 2s, risk rejections spike, Celery queue depth
- [ ] Log aggregation configured (CloudWatch, Datadog, Grafana Loki)
- [ ] Celery task failure alerts enabled

## Data

- [ ] Alembic migrations applied: `alembic upgrade head`
- [ ] Seed data applied if needed: `make seed`
- [ ] At least 6 months of historical bar data ingested for instruments you intend to trade/backtest
- [ ] RiskSnapshot task scheduled (cron daily before market open)

## Pre-go-live smoke test

- [ ] Register a new user account
- [ ] Create a strategy and run a backtest
- [ ] Create a paper portfolio and place a paper order
- [ ] Verify risk gate rejects an order with insufficient cash (set cash = $1, try to buy $100)
- [ ] Verify strategy deployment generates signals and creates orders
- [ ] Check Grafana shows non-zero metrics

## Rollback plan

- [ ] Previous Docker image tag noted
- [ ] Database backup taken immediately before deployment
- [ ] Rollback command documented: `docker compose up -d --no-deps api worker` with previous image tag
- [ ] Team knows how to run `alembic downgrade -1` if a migration needs reverting
