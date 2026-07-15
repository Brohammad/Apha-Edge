# Browser E2E (Playwright)

Smoke tests live in `frontend/e2e/`.

## What they cover

- Registration / login / logout
- Dashboard load
- Strategy creation
- Paper portfolio creation
- Orders / broker connection surface
- Deploy-to-paper UI presence
- Critical navigation (Backtests, Deployments, Marketplace, Orgs, Insights)

## Local

```bash
# Terminal A — API (Postgres + Redis required)
cd backend && RATE_LIMIT_ENABLED=false uvicorn alphaedge.main:app --reload

# Terminal B
cd frontend && npm run test:e2e
```

Or against a running demo gateway:

```bash
make demo
cd frontend && PLAYWRIGHT_BASE_URL=http://localhost:8080 npm run test:e2e
```

## CI

`.github/workflows/frontend-ci.yml` job `playwright` starts Postgres + Redis, migrates, boots the API, installs Chromium, and fails the workflow on regression.

## Note

`make test-e2e` runs **backend** HTTP e2e (`backend/tests/e2e`), not Playwright.
Use `cd frontend && npm run test:e2e` for browser smoke.
