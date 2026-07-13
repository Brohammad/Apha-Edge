# Troubleshooting

Common issues and how to resolve them.

---

## Backend

### `INTERNAL_ERROR` on all requests

**Symptom:** Every API call returns `{"error": {"code": "INTERNAL_ERROR", ...}}`.

**Causes & fixes:**
1. **Database not reachable.** Check `GET /api/v1/health/ready`. If `database` is `error`, verify `DATABASE_URL` and that Postgres is running.
2. **Missing migration.** Run `alembic upgrade head`.
3. **Bad secret.** If `CREDENTIALS_ENCRYPTION_KEY` is set but invalid, encrypted broker credentials will fail to decrypt. Rotate the key and re-enter credentials.

### `422 RISK_REJECTED` on order submission

The pre-trade risk gate rejected the order. The response body includes `stage` and `message`.

| Stage | Likely cause |
|-------|-------------|
| `cash_availability` | Order notional exceeds portfolio cash balance |
| `position_sizing` | Quantity is 0, or sell quantity exceeds holding |
| `max_position_exposure` | Order would make a single position too large |
| `portfolio_exposure` | Portfolio would become over-invested |
| `daily_loss_limit` | Portfolio has lost more than the configured % today |
| `risk_limits` | Max drawdown or VaR limit breached |

If no market data is available for the instrument, the gate rejects with `position_sizing` / `Cannot estimate fill price`. Ingest historical data first with `POST /api/v1/instruments/{id}/ingest`.

### Celery tasks not running

1. Check the worker container: `docker compose logs worker`.
2. Verify Redis is reachable: `redis-cli -u $REDIS_URL ping`.
3. Confirm the task is in `celery_app.conf.include`.

### `alembic upgrade head` fails with `relation already exists`

The database has a newer schema than Alembic's history. This usually means migrations were applied manually or from a different branch. Inspect with `alembic current` and `alembic history`.

### `ruff` or `mypy` CI failure

```bash
cd backend
ruff check src tests --fix     # auto-fix simple issues
ruff format src tests          # reformat
mypy src                       # type errors need manual fixes
```

---

## Frontend

### `npm audit` fails in CI

The audit level is `--audit-level=high`. Only critical/high vulnerabilities block CI.

```bash
cd frontend
npm audit                  # see full report
npm audit fix              # auto-fix compatible updates
npm audit fix --force      # force-update (may introduce breaking changes — review carefully)
```

### Vite dev server can't connect to API

Ensure the backend is running (`make dev` or `uvicorn alphaedge.main:app --reload`). The frontend Vite proxy is configured in `vite.config.ts` to forward `/api` requests to `http://localhost:8000`.

### Playwright tests fail locally

1. Install browser binaries: `npx playwright install --with-deps chromium`.
2. Ensure the frontend dev server is running: `npm run dev` (the playwright config auto-starts it).
3. Ensure the backend API is running with `RATE_LIMIT_ENABLED=false`.

---

## Docker Compose

### Port conflicts

If `5432`, `6379`, or `8000` are already in use:
- Change the host port mapping in `infrastructure/docker-compose.yml` (e.g. `"5433:5432"`).
- Update `DATABASE_URL` in `.env` accordingly.

### Data volume issues

```bash
# Reset everything (WARNING: destroys all local data)
docker compose -f infrastructure/docker-compose.yml down -v
docker compose -f infrastructure/docker-compose.yml up -d
```

---

## Environment validation

Run before starting the application:

```bash
python scripts/validate_env.py          # development checks
python scripts/validate_env.py --prod   # stricter production checks
```

Common failures:
- `MISSING JWT_SECRET_KEY` — copy from `.env.example` and generate a real secret.
- `INSECURE APP_SECRET_KEY` — replace the placeholder with `python -c "import secrets; print(secrets.token_hex(32))"`.

---

## Logs

The API emits structured JSON logs (structlog). Each log entry includes `request_id` for request correlation. In development, logs are pretty-printed to stdout.

```bash
# Follow API logs
docker compose -f infrastructure/docker-compose.yml logs -f api

# Filter by request_id
docker compose logs api 2>&1 | grep '"request_id": "abc-123"'
```

---

## Getting help

1. Check this document and `docs/LOCAL_DEVELOPMENT.md`.
2. Review `docs/RISK_MODEL.md` for risk-gate-specific issues.
3. Open an issue on GitHub with the full error response and log excerpt.
