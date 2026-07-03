# AlphaEdge

**A quantitative trading platform for designing strategies, backtesting them on historical data, managing portfolios, and placing paper (or live) trades — all from one web terminal.**

If you have never built a trading system before, think of AlphaEdge as four things in one:

1. **A strategy lab** — write trading rules in a simple YAML-like language or Python
2. **A time machine** — replay those rules on years of market data to see if they would have made money
3. **A portfolio desk** — track cash, holdings, risk, and performance
4. **An execution desk** — send orders to a paper broker (or a real broker when configured)

This README explains what every part does, how to run it locally, and how the pieces connect.

---

## Table of contents

- [What problem does AlphaEdge solve?](#what-problem-does-alphaedge-solve)
- [Core concepts (beginner-friendly)](#core-concepts-beginner-friendly)
- [What you can do in the app](#what-you-can-do-in-the-app)
- [How the system is built](#how-the-system-is-built)
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick start (local development)](#quick-start-local-development)
- [Using the web terminal](#using-the-web-terminal)
- [Authentication (email, Google, GitHub)](#authentication-email-google-github)
- [Market data & live prices](#market-data--live-prices)
- [API overview](#api-overview)
- [Testing](#testing)
- [Environment variables](#environment-variables)
- [Common issues](#common-issues)
- [Further reading](#further-reading)

---

## What problem does AlphaEdge solve?

Trading ideas are easy to have and hard to validate. Before risking real money you need to:

- Express a strategy in code
- Run it on historical prices
- Measure returns, drawdowns, and trade count
- Understand portfolio risk
- Practice execution in a simulated environment

AlphaEdge automates that research loop. You go from **idea → backtest → optimization → paper trading → (optional) live trading** without gluing together five different tools.

---

## Core concepts (beginner-friendly)

| Term | Meaning in AlphaEdge |
|------|----------------------|
| **Instrument** | A tradable symbol (e.g. `AAPL`, `SPY`) with exchange metadata |
| **Bar / OHLCV** | One candle of market data: open, high, low, close, volume for a time period |
| **Strategy** | Your trading logic — stored as a versioned document |
| **DSL** | Domain-specific language: YAML-style rules like “when SMA(10) crosses above SMA(30), buy” |
| **Backtest** | A historical simulation: the engine walks through past bars and pretends to trade |
| **Optimization** | Running many backtests with different parameters to find what worked best |
| **Portfolio** | A bucket of cash + holdings you track (paper or live) |
| **Order** | A request to buy or sell a quantity of an instrument |
| **Execution** | What happens when an order is filled by the broker (paper or Alpaca) |
| **Marketplace** | Publish strategies so other users can clone them (free or paid via Stripe mock) |
| **Insight** | AI-generated explanation of strategy behaviour (uses mock or OpenAI provider) |

---

## What you can do in the app

### 1. Identity & access
- Register with email/password
- Sign in with **Google** or **GitHub** OAuth
- Create **API keys** for programmatic access
- Email verification (auto-approved in development mode)

### 2. Strategies
- Create strategies in **DSL** or **Python**
- Version every change
- Validate & compile DSL (produces a compiled hash)
- Built-in indicators: SMA, EMA, RSI, MACD, Bollinger Bands, crossover helpers

### 3. Backtesting
- Submit a backtest job (runs asynchronously via **Celery**)
- Configure capital, slippage, commission, position sizing
- View equity curve, trade list, Sharpe ratio, max drawdown
- Optional **C++ engine** for faster DSL backtests (`make build-cpp`)

### 4. Optimization
- Grid-search parameters (e.g. fast/slow SMA periods)
- Rank trials by Sharpe, return, or drawdown

### 5. Portfolios & risk
- Create paper portfolios with starting capital
- View holdings and performance
- Compute risk metrics (VaR, beta, drawdown)
- Set risk limits and rebalance plans

### 6. Execution
- Connect a **paper broker** (built-in simulator)
- Submit market/limit orders with idempotency keys
- Track fills and execution history
- Optional **Alpaca** integration for paper/live (requires API keys)

### 7. Market data
- List instruments (AAPL, MSFT, GOOGL, SPY seeded by default)
- Ingest historical bars (mock, Alpha Vantage, or Polygon)
- **Live quote ticker** on the home page (Alpha Vantage when API key is set)

### 8. Marketplace & payments
- Organizations (teams/desks)
- Publish strategy listings (free or paid)
- Mock Stripe checkout for paid clones

### 9. Collaboration & AI
- Real-time collaboration sessions on strategies
- Request AI insights and strategy explanations

---

## How the system is built

AlphaEdge is a **modular monolith**: one deployable application, but code is split into clear domains (auth, strategies, backtests, etc.).

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser (React + Vite)          http://localhost:5173          │
│  Login · Dashboard · Strategies · Backtests · Orders · ...    │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST /api/v1  (proxied in dev)
┌────────────────────────────▼────────────────────────────────────┐
│  API (FastAPI + Python)          http://localhost:8000          │
│  Auth · Strategies · Backtests · Portfolios · Orders · ...      │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
┌──────▼──────┐   ┌───────▼───────┐   ┌──────▼──────┐
│ PostgreSQL  │   │    Redis      │   │   Celery    │
│ users,      │   │ cache, OAuth  │   │ backtests,  │
│ strategies, │   │ state, rate   │   │ orders,     │
│ bars, ...   │   │ limits        │   │ ingestion   │
└─────────────┘   └───────────────┘   └─────────────┘
```

**Async work** (backtests, order processing, data ingestion) is queued to Celery workers. The API returns immediately with a job ID; you poll or refresh the UI for status.

---

## Repository layout

```
alpha-edge/
├── backend/                 # Python API, domain logic, workers
│   ├── src/alphaedge/       # Application source
│   │   └── modules/         # Bounded contexts (identity, strategy, …)
│   ├── tests/               # unit/, integration/, e2e/
│   ├── alembic/             # Database migrations
│   ├── cpp/                 # Optional C++ backtest accelerator
│   └── scripts/             # seed_data, benchmarks, CLI tools
├── frontend/                # React web terminal (Vite)
│   ├── src/pages/           # One page per major feature
│   └── e2e/                 # Playwright user-journey tests
├── mobile/                  # React Native app (companion)
├── infrastructure/          # Docker Compose, nginx, AWS notes
├── docs/                    # Architecture & design deep-dives
├── Makefile                 # Common dev commands
└── .env.example             # Environment variable template
```

---

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| **Docker Desktop** | recent | Postgres + Redis locally |
| **Python** | 3.12+ | Backend API & workers |
| **Node.js** | 22+ | Frontend dev server |
| **Git** | any | Clone the repo |

Optional:
- **C++ compiler** — for the fast backtest extension
- **Alpha Vantage API key** — live ticker prices (free tier available)
- **Google / GitHub OAuth apps** — social login
- **Alpaca keys** — real/paper broker execution

---

## Quick start (local development)

### 1. Clone and configure

```bash
git clone <your-repo-url> alpha-edge
cd alpha-edge
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
APP_SECRET_KEY=<random-string>
JWT_SECRET_KEY=<random-string>
```

For live ticker prices, add:

```env
ALPHA_VANTAGE_API_KEY=<your-key>
```

### 2. Start databases

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
```

### 3. Install & migrate backend

```bash
make install
cd backend && alembic upgrade head
make seed          # roles, sample instruments (AAPL, MSFT, …), mock bars
```

### 4. Start backend services

**Terminal A — API:**

```bash
cd backend
source .venv/bin/activate   # if using a venv
RATE_LIMIT_ENABLED=false uvicorn alphaedge.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal B — Celery worker** (required for backtests & orders):

```bash
cd backend
source .venv/bin/activate
celery -A alphaedge.shared.infrastructure.celery_app worker --loglevel=info
```

### 5. Start frontend

**Terminal C:**

```bash
make frontend-dev
# → http://localhost:5173
```

### 6. Verify everything works

| Check | URL |
|-------|-----|
| Frontend | http://localhost:5173 |
| API health | http://localhost:8000/api/v1/health/ready |
| API docs (Swagger) | http://localhost:8000/api/v1/docs |

Or run the full automated suite:

```bash
make test-unit
make test-integration-local
make test-e2e          # API must be running on :8000
```

---

## Using the web terminal

After signing in you land on the **Overview** dashboard.

| Page | What it does |
|------|--------------|
| **Overview** | Stats, latest backtest chart, activity feed, quick-launch links |
| **Strategies** | Create/edit DSL or Python strategies, view versions |
| **Backtests** | Launch simulations, monitor status, open results |
| **Optimizer** | Parameter grid searches |
| **Portfolios** | Paper books, holdings, performance |
| **Orders** | Order blotter — submit and track paper orders |
| **Marketplace** | Browse/publish/clone strategy listings |
| **Organizations** | Team desks for marketplace publishing |
| **AI Insights** | Request narrative reports on strategies |

**Ticker tape** (top of every page): live prices for AAPL, MSFT, GOOGL, SPY when `ALPHA_VANTAGE_API_KEY` is set (green dot = live). Without a key it falls back to the latest stored database bars.

### Typical first-time workflow

1. **Register** at `/register`
2. **Create a strategy** → Strategies → New strategy (DSL template pre-filled)
3. **Validate** the strategy version on its detail page
4. **Run a backtest** → Backtests → Launch (pick strategy version + instrument + date range)
5. Wait for status `completed` (Celery worker must be running)
6. **Create a portfolio** → Portfolios → New portfolio
7. **Place a paper order** → Orders → connect paper broker if prompted

---

## Authentication (email, Google, GitHub)

### Email / password
Works out of the box. Passwords must meet strength requirements. In `development` mode, email is auto-verified on registration.

### OAuth setup

OAuth uses a **two-step redirect**:

```
Browser → Google/GitHub → Backend callback (:8000) → Frontend (/oauth/callback)
```

Register these **exact** callback URLs in your provider consoles:

| Provider | Authorized redirect URI |
|----------|-------------------------|
| Google | `http://localhost:8000/api/v1/auth/oauth/google/callback` |
| GitHub | `http://localhost:8000/api/v1/auth/oauth/github/callback` |

Also add **JavaScript origin** (Google only): `http://localhost:5173`

Put credentials in `.env`:

```env
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GITHUB_OAUTH_CLIENT_ID=...
GITHUB_OAUTH_CLIENT_SECRET=...
OAUTH_REDIRECT_BASE_URL=http://localhost:8000/api/v1/auth/oauth
OAUTH_FRONTEND_CALLBACK_URL=http://localhost:5173/oauth/callback
```

Restart the API after changing `.env`.

**Google "Access blocked"?** Your OAuth app is in *Testing* mode — add your Gmail under **OAuth consent screen → Test users**.

**GitHub `redirect_uri_mismatch`?** Ensure the callback URL in the GitHub OAuth App settings matches exactly, and that `GITHUB_OAUTH_CLIENT_ID` in `.env` matches the app you configured.

---

## Market data & live prices

### Seeded data
`make seed` creates four instruments and 30 days of **mock** historical bars. Good for backtesting demos, not for live prices.

### Live ticker
Set `ALPHA_VANTAGE_API_KEY` in `.env`. The home page ticker calls:

```
GET /api/v1/market-data/quotes?symbols=AAPL,MSFT,GOOGL,SPY
```

Quotes are cached for 5 minutes to respect API rate limits.

### Historical ingestion (admin)
Admins can trigger ingestion:

```
POST /api/v1/market-data/ingest
{
  "provider": "alpha_vantage",
  "symbols": ["AAPL"],
  "timeframe": "1d",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2026-01-01T00:00:00Z"
}
```

Providers: `mock`, `alpha_vantage`, `polygon` (requires respective API keys).

---

## API overview

- **Base URL (local):** `http://localhost:8000/api/v1`
- **Interactive docs:** `http://localhost:8000/api/v1/docs`
- **Auth:** `Authorization: Bearer <access_token>` or `X-API-Key: ae_live_...`
- **Response shape:** `{ "data": { ... }, "meta": { "request_id": "..." } }`

### Major endpoint groups (63 routes)

| Group | Prefix | Examples |
|-------|--------|----------|
| Health | `/health/` | `live`, `ready` |
| Auth | `/auth/` | `register`, `login`, `me`, `oauth/{provider}`, `api-keys` |
| Instruments | `/instruments/` | list, bars, latest bar |
| Market data | `/market-data/` | `quotes`, `ingest` |
| Strategies | `/strategies/` | CRUD, versions, validate |
| Indicators | `/indicators/` | list built-in indicators |
| Backtests | `/backtest-runs/` | submit, result, equity-curve, trades |
| Optimization | `/optimization-runs/` | submit, trials, best result |
| Portfolios | `/portfolios/` | CRUD, holdings, performance, risk |
| Execution | `/broker-connections/`, `/orders/` | paper broker, submit/cancel orders |
| Marketplace | `/marketplace/listings` | publish, clone |
| Payments | `/payments/` | mock Stripe checkout |
| Organizations | `/organizations/` | team desks |
| Insights | `/insights/` | AI reports |
| Collaboration | `/collaboration/sessions` | shared editing |

See [docs/architecture/API_OVERVIEW.md](docs/architecture/API_OVERVIEW.md) for the full reference.

---

## Testing

```bash
# Unit tests (fast, no Docker)
make test-unit

# All backend tests (integration skips if DB down)
make test

# Integration (starts Docker Postgres + Redis)
make test-integration

# End-to-end HTTP test (API must be running, rate limits off)
make test-e2e

# Frontend user-journey (browser automation)
cd frontend && npx playwright test e2e/user-journey.spec.ts

# Optional: C++ engine benchmark
make build-cpp && make benchmark
```

CI runs backend unit + integration tests on every PR via GitHub Actions.

---

## Environment variables

Copy `.env.example` to `.env` in the repo root. Key variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `APP_ENV` | `development` / `production` / `test` | `development` |
| `APP_SECRET_KEY` | App-wide secret | change-me |
| `DATABASE_URL` | Postgres connection | `postgresql+asyncpg://alphaedge:alphaedge@localhost:5432/alphaedge` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Token signing | change-me |
| `CORS_ORIGINS` | Allowed frontend origins | `["http://localhost:5173"]` |
| `ALPHA_VANTAGE_API_KEY` | Live quotes & ingestion | empty |
| `POLYGON_API_KEY` | Polygon market data | empty |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | Google login | empty |
| `GITHUB_OAUTH_CLIENT_ID/SECRET` | GitHub login | empty |
| `OAUTH_REDIRECT_BASE_URL` | Backend OAuth callback base | `http://localhost:8000/api/v1/auth/oauth` |
| `OAUTH_FRONTEND_CALLBACK_URL` | Post-login frontend URL | `http://localhost:5173/oauth/callback` |
| `ALPACA_API_KEY/SECRET` | Broker execution | empty |
| `OPENAI_API_KEY` | AI insights (`LLM_PROVIDER=openai`) | empty |
| `RATE_LIMIT_ENABLED` | API rate limiting | `true` (set `false` for local e2e) |
| `LIVE_TRADING_ENABLED` | Allow live (non-paper) orders | `false` |
| `CPP_ENGINE` | C++ backtest: `auto` / `off` / `require` | `auto` |

---

## Common issues

| Symptom | Fix |
|---------|-----|
| `database: error` on `/health/ready` | Start Docker Postgres: `docker compose -f infrastructure/docker-compose.yml up -d postgres redis` |
| Backtest stuck on `queued` | Start Celery worker (see Quick start) |
| OAuth redirects back to login | Ensure OAuth callback URLs match exactly; restart API after `.env` changes |
| Google "Access blocked" | Add your email as a test user in Google Cloud Console |
| GitHub `redirect_uri_mismatch` | Callback must be `http://localhost:8000/api/v1/auth/oauth/github/callback` |
| Stale AAPL price on home page | Set `ALPHA_VANTAGE_API_KEY` and restart API |
| `429 Rate limit exceeded` during tests | Start API with `RATE_LIMIT_ENABLED=false` |
| `Admin role required` creating instruments | Use seed data or an admin account; instrument creation is admin-only in dev |

---

## Makefile reference

| Command | Description |
|---------|-------------|
| `make install` | Install Python dependencies |
| `make dev` | Docker Compose full stack |
| `make migrate` | Run Alembic migrations |
| `make seed` | Seed roles, instruments, mock bars |
| `make frontend-dev` | Start Vite dev server |
| `make test-unit` | Unit tests only |
| `make test-integration` | Integration tests with Docker |
| `make test-e2e` | Full HTTP end-to-end test |
| `make build-cpp` | Build C++ backtest accelerator |
| `make lint` | Ruff + mypy on backend |

---

## Further reading

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture/ARCHITECTURE.md) | Bounded contexts, events, deployment |
| [Repository Structure](docs/architecture/REPOSITORY_STRUCTURE.md) | Code organization conventions |
| [Database Schema](docs/architecture/DATABASE_SCHEMA.md) | Tables and relationships |
| [API Design](docs/architecture/API_OVERVIEW.md) | Full endpoint reference |
| [Roadmap](docs/ROADMAP.md) | Planned features |
| [Live Trading Runbook](docs/LIVE_TRADING_RUNBOOK.md) | Production trading checklist |

---

## Tech stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic |
| Data | PostgreSQL 16, Redis 7 |
| Jobs | Celery |
| Performance | C++17 + pybind11 (optional backtest engine) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Mobile | React Native (companion app in `/mobile`) |
| Infra | Docker Compose, GitHub Actions, Nginx |
| Payments | Stripe (mock gateway for local dev) |
| Brokers | Paper simulator, Alpaca |

---

## License

Proprietary — All rights reserved.
