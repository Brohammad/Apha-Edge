# AlphaEdge Frontend

React web terminal for AlphaEdge. See the **[main README](../README.md)** for full platform documentation, setup, and feature overview.

## Quick commands

```bash
npm install
npm run dev          # http://localhost:5173 (proxies /api → localhost:8000)
npm run build
npm run lint
npx playwright test e2e/user-journey.spec.ts   # browser E2E
```

## Structure

- `src/pages/` — one page per feature (strategies, backtests, orders, …)
- `src/lib/api.ts` — REST client (JWT in memory, refresh token in httpOnly cookie)
- `src/lib/auth.tsx` — login, register, OAuth session handling
- `e2e/` — Playwright user-journey tests
