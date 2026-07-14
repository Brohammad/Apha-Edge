# AlphaEdge — Public Demo Deployment

One URL serves the **web terminal** and **API** (nginx gateway). No API keys required — uses mock LLM and seeded market data.

---

## Quick start (local demo)

```bash
# From repo root
make demo
```

Open **http://localhost:8080**

### Demo login

| Field | Value |
|-------|-------|
| Email | `demo@example.com` |
| Password | `DemoAlphaEdge1!` |

Or register a new account at `/register` (email auto-verified in demo mode).

### Stop

```bash
make demo-down
```

---

## What runs

| Service | Role |
|---------|------|
| `gateway` | Production React build + nginx (`:8080`) |
| `api` | FastAPI — migrates DB, seeds data on first boot |
| `worker` | Celery (backtests, orders) |
| `postgres` / `redis` | Data layer (internal only) |

Config: `.env.demo` (copy from `.env.demo.example`).

---

## First-boot seeding

When `RUN_DEMO_SEED=true` in `.env.demo`, the API container runs on startup:

1. `alembic upgrade head`
2. `scripts.seed_data` — roles, AAPL/MSFT/GOOGL/SPY, 30 days mock bars
3. `scripts.seed_demo_user` — demo account above

Re-seed manually:

```bash
docker compose -p alphaedge-demo -f infrastructure/docker-compose.demo.yml exec api \
  sh -c 'PYTHONPATH=/app/src:/app python -m scripts.seed_data && python -m scripts.seed_demo_user'
```

---

## Deploy to a VPS (portfolio URL)

1. Provision a small VM (2 GB RAM, Docker installed).
2. Clone the repo, copy `.env.demo.example` → `.env.demo`.
3. **Generate new secrets** for `APP_SECRET_KEY` and `JWT_SECRET_KEY`.
4. Set `CORS_ORIGINS` to your public URL, e.g. `["https://demo.yourdomain.com"]`.
5. Point DNS to the VM; terminate TLS with Caddy or Certbot in front of port 8080.
6. Run:

```bash
make demo
```

7. Add the public URL to your README and case study.

---

## Deploy to Render / Fly (outline)

**Render:** Create a Blueprint with managed Postgres, Redis, web service (API Dockerfile), background worker, and static site — or run the all-in-one `docker-compose.demo.yml` on a Render private service.

**Fly.io:** `fly launch` with `docker-compose.demo.yml` adapted to Fly volumes; expose gateway on `fly.toml` `internal_port = 80`.

For a portfolio, a **$5–6/mo VPS + `make demo`** is usually simpler than multi-service PaaS.

---

## Screenshots for README

With the demo running, capture:

1. `http://localhost:8080/` — dashboard  
2. `/strategies` — strategy editor  
3. `/backtests` — completed run  
4. `/orders` — paper broker + blotter  
5. `/live-chart` — candlestick panel  

Save PNGs to `docs/screenshots/` per `docs/screenshots/README.md`.

---

## Security notes (public demo)

- **Do not** enable `LIVE_TRADING_ENABLED` on a public demo.
- Rotate JWT/APP secrets before exposing to the internet.
- Use `RATE_LIMIT_ENABLED=true` if you expect traffic.
- Demo password is public — never reuse it elsewhere.
