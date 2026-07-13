# Local Development Guide

Everything you need to run AlphaEdge locally from scratch.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | `pyenv` recommended |
| Node.js | 22+ | `nvm` recommended |
| Docker Desktop | Latest | Includes Docker Compose v2 |
| Git | 2.x | |

Optional but recommended:
- `direnv` — auto-load `.env` when entering the project directory
- `make` — task runner (pre-installed on macOS/Linux)

---

## One-command setup

```bash
git clone https://github.com/your-org/alpha-edge.git
cd alpha-edge
cp .env.example .env    # review and fill in any API keys you have

# Start Postgres + Redis, install backend, build C++ ext, apply migrations
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
make setup
```

Then start the full stack:

```bash
make dev          # Docker Compose — API + worker + Postgres + Redis
# OR split terminals:
make frontend-dev   # Vite dev server at http://localhost:5173
uvicorn alphaedge.main:app --reload   # API at http://localhost:8000
```

---

## Manual step-by-step

### 1. Start infrastructure

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
```

### 2. Install backend

```bash
cd backend
pip install -e ".[dev]"
pip install ./cpp          # optional C++ position-sizing extension
```

### 3. Configure environment

```bash
cp .env.example .env
# Minimum required values for local dev are already set in .env.example
# You only need to fill in POLYGON_API_KEY / OPENAI_API_KEY if you want
# live quotes or AI insights. Set QUOTE_PROVIDER=mock and LLM_PROVIDER=mock
# to work fully offline.
python scripts/validate_env.py
```

### 4. Apply database migrations

```bash
cd backend
alembic upgrade head
```

### 5. Run the API

```bash
# From the backend directory
PYTHONPATH=src uvicorn alphaedge.main:app --reload --host 0.0.0.0 --port 8000
```

Or via Docker Compose (includes the Celery worker):

```bash
docker compose -f infrastructure/docker-compose.yml up api worker
```

### 6. Run the frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
```

---

## Environment variables

See `.env.example` for full documentation. The minimum set for local development:

```env
DATABASE_URL=postgresql+asyncpg://alphaedge:alphaedge@localhost:5432/alphaedge
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
JWT_SECRET_KEY=any-local-dev-secret
APP_SECRET_KEY=any-local-dev-secret
QUOTE_PROVIDER=mock
LLM_PROVIDER=mock
```

---

## Running tests

```bash
# Unit tests (no DB or Redis required)
make test-unit

# Integration tests (requires Postgres + Redis from Docker Compose)
make test-integration-local

# Full test suite
make test

# Frontend linting
make frontend-lint

# Frontend e2e tests (requires running frontend + API)
cd frontend && npx playwright test
# Install browser binaries first if needed:
npx playwright install --with-deps chromium
```

---

## Makefile reference

| Target | Description |
|--------|-------------|
| `make setup` | Install backend + build C++ + apply migrations |
| `make dev` | Start full stack via Docker Compose |
| `make dev-down` | Stop Docker Compose stack |
| `make check` | Lint + unit tests (fast, no DB) |
| `make lint` | Ruff (lint + format); run `make lint-types` for mypy |
| `make test-unit` | Unit tests only |
| `make test-integration` | Integration tests (starts Docker services) |
| `make test-integration-local` | Integration tests (assumes services already running) |
| `make test-e2e` | End-to-end tests (starts Docker, starts API) |
| `make migrate` | Apply all pending Alembic migrations |
| `make migrate-create msg="..."` | Generate a new migration |
| `make seed` | Seed demo data |
| `make frontend-dev` | Start Vite dev server |
| `make frontend-build` | Production build of frontend |
| `make frontend-lint` | Lint frontend with oxlint |
| `make ci-local` | Mirror CI: lint + unit + integration |
| `make benchmark` | Run the C++ backtest benchmark |

---

## Useful API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health/ready` | Check DB + Redis connectivity |
| `GET /api/v1/docs` | Interactive API docs (dev only) |
| `POST /api/v1/auth/register` | Create an account |
| `POST /api/v1/auth/login` | Get JWT tokens |
| `GET /api/v1/metrics` | Prometheus metrics (requires auth in prod) |

---

## Observability (optional)

```bash
# Start Prometheus + Grafana alongside the main stack
docker compose -f infrastructure/docker-compose.yml --profile observability up -d

# Grafana: http://localhost:3001 (admin / alphaedge)
# Prometheus: http://localhost:9090
```

Add a Prometheus datasource in Grafana pointing to `http://prometheus:9090`. The `AlphaEdge API` dashboard is pre-loaded.

---

## Common issues

See `docs/TROUBLESHOOTING.md` for a full list. Quick fixes:

- **Port conflicts** — change host port mappings in `infrastructure/docker-compose.yml`.
- **Migrations fail** — ensure Postgres is healthy: `docker compose ps`.
- **Imports fail** — ensure `PYTHONPATH=src` is set or run from the `backend/` directory with the package installed (`pip install -e ".[dev]"`).
