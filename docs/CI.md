# CI — Continuous Integration

AlphaEdge uses GitHub Actions for automated checks on every push and pull request to `main`.

## Workflows

### `backend-ci.yml`

Runs on changes to `backend/**`.

| Step | Command | Notes |
|------|---------|-------|
| Install | `pip install -e "./backend[dev]"` | Includes dev extras (pytest, ruff, mypy) |
| Build C++ ext | `pip install ./backend/cpp` | Optional position-sizing speedup |
| Lint | `ruff check src tests && ruff format --check src tests` | Fail on any lint error |
| Type check | `make lint-types` (`mypy src`) | **Local only** — gradual typing; not in CI until backlog cleared |
| Security audit | `pip-audit -r /tmp/reqs.txt` | Filters editable/local packages to avoid false positives |
| Migrations | `alembic upgrade head` | Applied against in-workflow Postgres |
| Tests | `pytest -v --cov=alphaedge` | Full suite (unit + integration) |

Services started in CI: PostgreSQL 16, Redis 7.

### `frontend-ci.yml`

Runs on changes to `frontend/**` or `backend/**` (Playwright needs the API).

| Job | Steps |
|-----|-------|
| `build` | `npm ci` → lint → `npm audit` → `npm run build` |
| `playwright` | Postgres + Redis → migrate → start API → Chromium → `npm run test:e2e` |

Browser smoke fails CI on regression. See [BROWSER_TESTING.md](BROWSER_TESTING.md).

Local Playwright: `cd frontend && npm run test:e2e` (API must be on `:8000`).  
`make test-e2e` is **backend** HTTP e2e, not Playwright.

## Running CI locally

```bash
# Mirror backend CI (lint + unit tests — no DB required)
make check

# Optional: mypy gradual typing (local only, not CI-gated)
make lint-types

# Full CI including integration tests (requires Postgres + Redis)
make ci-local

# Start Postgres + Redis for integration tests
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
```

## Environment variables in CI

The following secrets are injected by GitHub Actions:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Points to the in-workflow Postgres service |
| `REDIS_URL` | Points to the in-workflow Redis service |
| `JWT_SECRET_KEY` | Fixed test value (`test-secret-key`) |
| `APP_SECRET_KEY` | Fixed test value (`test-app-secret`) |

External API keys (Polygon, OpenAI) are not required for CI — the test suite uses mock providers.

## Skipping CI

Add `[skip ci]` to your commit message to skip all workflow runs.
