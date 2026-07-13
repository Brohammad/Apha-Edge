# Deployment Guide

This document covers deploying AlphaEdge to production using Docker Compose (small scale) or Kubernetes (production scale).

## Prerequisites

- Docker ≥ 24 and Docker Compose v2
- PostgreSQL 16 and Redis 7 (can be managed services: RDS, ElastiCache)
- A registered domain with TLS (Let's Encrypt or ACM)
- Environment variables configured — see `.env.example` and `docs/LOCAL_DEVELOPMENT.md`

---

## Option 1: Docker Compose (single-server)

Suitable for staging or low-traffic production deployments.

```bash
# 1. Clone the repo and configure the environment
git clone https://github.com/your-org/alpha-edge.git
cd alpha-edge
cp .env.example .env
# Edit .env — set all [REQUIRED IN PROD] variables
python scripts/validate_env.py --prod

# 2. Start the stack (API + worker + Postgres + Redis)
docker compose -f infrastructure/docker-compose.yml up -d

# 3. Apply database migrations
docker compose -f infrastructure/docker-compose.yml exec api alembic upgrade head

# 4. (Optional) Start observability stack
docker compose -f infrastructure/docker-compose.yml --profile observability up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI application |
| `worker` | — | Celery worker (async tasks) |
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 (cache, broker, results) |
| `prometheus` | 9090 | Metrics scraper (observability profile) |
| `grafana` | 3001 | Dashboard UI (observability profile) |

---

## Option 2: Kubernetes

See `infrastructure/k8s/alphaedge.yaml` for a starting-point manifest. At minimum you will need to:

1. Create a `ConfigMap` and `Secret` for environment variables.
2. Set up a `PersistentVolumeClaim` for Postgres data (or use RDS).
3. Create an `Ingress` resource with TLS.

```bash
kubectl apply -f infrastructure/k8s/alphaedge.yaml
kubectl rollout status deployment/alphaedge-api
```

---

## Environment variables

All required variables are documented in `.env.example`. Key production requirements:

| Variable | How to generate |
|----------|----------------|
| `APP_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CREDENTIALS_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |

---

## Database migrations

Migrations are managed by Alembic.

```bash
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# Roll back one revision
alembic downgrade -1
```

Always run migrations before deploying a new version of the API.

---

## Health checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health/live` | Liveness — is the process alive? |
| `GET /api/v1/health/ready` | Readiness — DB and Redis reachable? |

Configure your load balancer to use `/api/v1/health/ready` as the health check target.

---

## Nginx reverse proxy

A sample Nginx config is in `infrastructure/nginx/nginx.conf`. Key settings:

- Proxy WebSocket connections with `Upgrade` and `Connection` headers.
- Enable `proxy_read_timeout 300` for long-running backtest requests.
- Add `limit_req` for additional rate limiting in front of the application.

---

## Observability

After deploying the observability profile:

1. Open Grafana at `http://<host>:3001` (default login: `admin` / `alphaedge`).
2. Add a Prometheus datasource pointing to `http://prometheus:9090`.
3. The `AlphaEdge API` dashboard is pre-loaded from `infrastructure/grafana/dashboards/alphaedge-api.json`.

---

## Secrets management

In production, inject secrets via:
- **AWS Secrets Manager** — pull secrets at container startup with a sidecar or init container.
- **Kubernetes Secrets** — mount as environment variables.
- **HashiCorp Vault** — recommended for multi-region deployments.

Never commit `.env` to source control.

---

## Rollback

```bash
# Docker Compose — redeploy previous image tag
docker compose -f infrastructure/docker-compose.yml up -d --no-deps api worker

# Roll back migration if needed
alembic downgrade -1
```

See `docs/PRODUCTION_CHECKLIST.md` before going live.
