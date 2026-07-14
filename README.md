# AlphaEdge

**A quantitative trading platform for designing strategies, backtesting them on historical data, managing portfolios, and placing paper (or live) trades — all from one web terminal.**

> **Portfolio snapshot** · [Case study](docs/CASE_STUDY.md) · [Interview prep](docs/INTERVIEW_TALKING_POINTS.md)
>
> | | |
> |---|---|
> | **Tests** | 144 automated (unit + integration + e2e) |
> | **Coverage** | ~58% unit test line coverage |
> | **Architecture** | 19 bounded contexts, modular monolith |
> | **Performance** | C++ backtest core ~78× faster than Python (1M-bar benchmark) |
> | **Stack** | FastAPI · Celery · PostgreSQL · Redis · React 19 · C++17 |

If you have never built a trading system before, think of AlphaEdge as four things in one:

1. **A strategy lab** — write trading rules in a simple YAML-like language or Python
2. **A time machine** — replay those rules on years of market data to see if they would have made money
3. **A portfolio desk** — track cash, holdings, risk, and performance
4. **An execution desk** — send orders to a paper broker (or a real broker when configured)

This README explains what every part does, how to run it locally, and how the pieces connect.

**Start here:** [Complete project guide](#complete-project-guide) — narrative walkthrough, architecture, and copy-paste setup scripts.

---

## Table of contents

- [Complete project guide](#complete-project-guide)
- [Portfolio & interview materials](#portfolio--interview-materials)
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
- [Strategy guide](docs/STRATEGY_GUIDE.md) — DSL, Python runtime, deployments
- [Testing](#testing)
- [Environment variables](#environment-variables)
- [Known limitations](#known-limitations)
- [Common issues](#common-issues)
- [Makefile reference](#makefile-reference)
- [Further reading](#further-reading)
- [Tech stack](#tech-stack)

---

## Portfolio & interview materials

| Document | Use |
|----------|-----|
| [Case study](docs/CASE_STUDY.md) | Send to recruiters / hiring managers (architecture + decisions) |
| [Interview talking points](docs/INTERVIEW_TALKING_POINTS.md) | 5 stories for system-design interviews |
| [Engineering audit](docs/ENGINEERING_AUDIT_V1.md) | Honest capability matrix + technical debt |
| [Screenshots](docs/screenshots/) | Add PNGs for README hero (see `docs/screenshots/README.md`) |

**Elevator pitch:** *"I built a quant research terminal — DSL compiler, C++ backtest accelerator, pre-trade risk gate, and paper-to-live execution — as a modular monolith with 144 tests."*

---

## Complete project guide

This section is the **full story** of AlphaEdge: what it is, how the pieces talk to each other, and the exact commands to go from zero to a running backtest.

### What you are looking at

AlphaEdge is a **quantitative trading research platform** shipped as a single repository with three runnable surfaces:

| Surface | Path | Role |
|---------|------|------|
| **Web terminal** | `frontend/` | Where humans design strategies, launch backtests, manage portfolios, and place orders |
| **API + workers** | `backend/` | Business logic, database, async jobs (backtests, ingestion, order execution) |
| **Mobile companion** | `mobile/` | Read-only / lightweight companion (optional) |

The backend is a **modular monolith**: one deployable app, but code is split into **bounded contexts** (identity, strategy, backtesting, execution, …). Each context has `domain/` → `application/` → `infrastructure/` → `presentation/` layers.

### The research loop (what the product is for)

```
  ┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
  │ 1. Author   │────▶│ 2. Validate  │────▶│ 3. Backtest │────▶│ 4. Optimize  │
  │ DSL/Python  │     │ compile hash │     │ Celery job  │     │ grid search  │
  └─────────────┘     └──────────────┘     └──────┬──────┘     └──────────────┘
                                                   │
                     ┌──────────────┐     ┌────────▼────────┐     ┌──────────────┐
                     │ 6. Live/manual│◀────│ 5. Paper deploy │────▶│ AI insights  │
                     │ orders/Alpaca │     │ bar → signal    │     │ explanations │
                     └──────────────┘     └─────────────────┘     └──────────────┘
```

1. **Author** — Write rules in YAML (DSL) or Python (`StrategyBase`).
2. **Validate** — Compiler checks syntax, indicators, and dangerous Python imports.
3. **Backtest** — Event-driven simulator replays historical bars; outputs equity curve + metrics.
4. **Optimize** — Run hundreds of backtests with different parameters (Celery-parallel).
5. **Deploy to paper** — Attach a validated strategy to a paper broker; new bars trigger signals → orders.
6. **Execute** — Manual orders or Alpaca (when configured); portfolio and risk modules track exposure.

### How requests flow through the system

```mermaid
flowchart TB
    subgraph browser [Browser localhost:5173]
        UI[React pages]
    end
    subgraph api [FastAPI localhost:8000]
        R[REST routers]
        H[Command handlers]
    end
    subgraph data [Data layer]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end
    subgraph async [Celery workers]
        BT[execute_backtest]
        OR[execute_order]
        ING[run_ingestion]
    end
    UI -->|JWT or API key| R
    R --> H
    H --> PG
    H -->|enqueue| RD
    RD --> BT
    RD --> OR
    RD --> ING
    BT --> PG
    ING -->|upsert bars| PG
    ING -->|evaluate deployments| OR
```

**Synchronous path:** login, list strategies, validate version — API reads/writes Postgres and returns immediately.

**Asynchronous path:** backtest submit → row in `backtest_runs` with status `queued` → Celery worker runs `BacktestEngine` → status `completed` + results. Same pattern for orders and market-data ingestion.

### Backend modules (what each folder does)

| Module | `backend/src/alphaedge/modules/` | Responsibility |
|--------|----------------------------------|----------------|
| **identity** | `identity/` | Users, JWT, OAuth, API keys, RBAC |
| **market_data** | `market_data/` | Instruments, OHLCV bars, quotes, ingestion |
| **strategy** | `strategy/` | DSL compiler, Python sandbox, versions, **deployments** |
| **backtesting** | `backtesting/` | Event engine, fills, metrics, C++ bridge |
| **optimization** | `optimization/` | Grid / walk-forward / Optuna / genetic search |
| **portfolio** | `portfolio/` | Holdings, cash, performance snapshots |
| **risk** | `risk/` | VaR, Sharpe, drawdown, limits |
| **execution** | `execution/` | Paper broker, Alpaca, order lifecycle |
| **insights** | `insights/` | ChatGPT / mock strategy reports |
| **marketplace** | `marketplace/` | Publish & clone strategies |
| **collaboration** | `collaboration/` | WebSocket co-editing |
| **payments** | `payments/` | Stripe checkout for paid clones |
| **organization** | `organization/` | Team desks |

Shared infrastructure lives in `backend/src/alphaedge/shared/` (database, Celery, Redis, logging).

### Strategy engine (the core)

Two authoring modes, one runtime concept:

| | DSL (YAML) | Python |
|---|-----------|--------|
| **Example** | `when: crossover(sma(10), sma(30))` → `BUY` | `class S(StrategyBase): def on_bar(...)` |
| **Backtest** | Python engine or C++ (simple crossover only) | Python engine only |
| **Deploy** | Yes | Yes |

Full DSL reference: [docs/STRATEGY_GUIDE.md](docs/STRATEGY_GUIDE.md).

**Versioning:** Every save creates a new `strategy_version`. Backtests and deployments pin a specific version id. You must **validate** before backtesting.

**Paper deployment:** `POST /api/v1/strategy-deployments` links a version → portfolio → paper broker → instruments. When ingestion writes a bar, the deployment runner evaluates signals and submits orders.

### One-shot bootstrap script

Run from the repository root after cloning. Requires Docker, Python 3.12+, and Node 22+.

```bash
#!/usr/bin/env bash
# AlphaEdge local bootstrap — run from repo root
set -euo pipefail

# 1. Environment
cp -n .env.example .env 2>/dev/null || true
echo ">>> Edit .env and set APP_SECRET_KEY, JWT_SECRET_KEY (and optional API keys)"

# 2. Infrastructure
docker compose -f infrastructure/docker-compose.yml up -d postgres redis

# 3. Backend
make install
make migrate
make seed

# 4. Instructions for parallel terminals
cat <<'EOF'

AlphaEdge is installed. Open THREE terminals:

  Terminal A — API:
    cd backend && source .venv/bin/activate
    RATE_LIMIT_ENABLED=false uvicorn alphaedge.main:app --host 127.0.0.1 --port 8000 --reload

  Terminal B — Celery (required for backtests & orders):
    cd backend && source .venv/bin/activate
    celery -A alphaedge.shared.infrastructure.celery_app worker --loglevel=info

  Terminal C — Frontend:
    make frontend-dev
    → http://localhost:5173

Health check: curl -s http://localhost:8000/api/v1/health/ready | jq

EOF
```

Save as `scripts/bootstrap-dev.sh` or paste into your shell.

### End-to-end demo script (API + UI)

After bootstrap, this is the **happy path** a new developer should follow:

```bash
# --- 1. Register and login (or use the UI at /register) ---
BASE=http://localhost:8000/api/v1
EMAIL="dev@example.com"
PASS="SecurePass123!"

curl -s -X POST "$BASE/auth/register" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"display_name\":\"Dev\"}" | jq

TOKEN=$(curl -s -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" | jq -r '.data.access_token')

AUTH="Authorization: Bearer $TOKEN"

# --- 2. List seeded instruments ---
curl -s "$BASE/instruments?limit=5" -H "$AUTH" | jq '.data.items[].symbol'
INSTRUMENT_ID=$(curl -s "$BASE/instruments?limit=1" -H "$AUTH" | jq -r '.data.items[0].id')

# --- 3. Create a DSL strategy ---
STRATEGY=$(curl -s -X POST "$BASE/strategies" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{
    "name": "demo-golden-cross",
    "strategy_type": "dsl",
    "source_code": "name: golden-cross\nparameters:\n  fast: 10\n  slow: 30\nsignals:\n  - when: crossover(sma(fast), sma(slow))\n    then: BUY\n  - when: crossunder(sma(fast), sma(slow))\n    then: SELL\n"
  }')
STRATEGY_ID=$(echo "$STRATEGY" | jq -r '.data.id')
VERSION_ID=$(curl -s "$BASE/strategies/$STRATEGY_ID/versions" -H "$AUTH" | jq -r '.data.items[0].id')

# --- 4. Validate ---
curl -s -X POST "$BASE/strategies/$STRATEGY_ID/versions/$VERSION_ID/validate" -H "$AUTH" | jq

# --- 5. Submit backtest (Celery worker must be running) ---
RUN=$(curl -s -X POST "$BASE/backtest-runs" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{
    \"strategy_version_id\": \"$VERSION_ID\",
    \"name\": \"Demo run\",
    \"config\": {
      \"instrument_ids\": [\"$INSTRUMENT_ID\"],
      \"timeframe\": \"1d\",
      \"start_date\": \"2025-01-01T00:00:00+00:00\",
      \"end_date\": \"2025-12-31T00:00:00+00:00\",
      \"initial_capital\": \"100000\",
      \"allow_short\": false,
      \"position_sizing\": {\"model\": \"fixed_quantity\", \"value\": 10}
    }
  }")
RUN_ID=$(echo "$RUN" | jq -r '.data.id')
echo "Backtest run id: $RUN_ID — poll: curl -s $BASE/backtest-runs/$RUN_ID -H \"$AUTH\" | jq '.data.status'"

# --- 6. When status=completed, fetch results ---
# curl -s "$BASE/backtest-runs/$RUN_ID/result" -H "$AUTH" | jq
```

The same flow is available in the UI: **Strategies → Validate → Backtests → Launch**.

### Frontend pages map

| Route | Page | Backend modules touched |
|-------|------|-------------------------|
| `/` | Dashboard | backtesting, market_data, portfolios |
| `/strategies` | Strategy list | strategy |
| `/strategies/:id` | Editor, deploy, validate | strategy, collaboration |
| `/backtests` | Launch & monitor runs | backtesting |
| `/backtests/:id` | Equity curve, trades | backtesting |
| `/optimizations` | Parameter search | optimization, backtesting |
| `/portfolios` | Holdings | portfolio, risk |
| `/orders` | Order blotter | execution |
| `/marketplace` | Listings | marketplace, payments |
| `/insights` | AI reports | insights |

### Database & migrations

- **ORM:** SQLAlchemy 2.0 async
- **Migrations:** Alembic in `backend/alembic/versions/` (run `make migrate`)
- **Seed:** `make seed` — roles, admin user pattern, AAPL/MSFT/GOOGL/SPY, 30 days mock bars

Key tables: `users`, `strategies`, `strategy_versions`, `strategy_deployments`, `backtest_runs`, `backtest_results`, `bars`, `orders`, `portfolios`, `holdings`.

Schema diagram: [docs/architecture/DATABASE_SCHEMA.md](docs/architecture/DATABASE_SCHEMA.md).

### Optional: C++ backtest accelerator

```bash
make build-cpp          # builds alphaedge_cpp pybind11 module
CPP_ENGINE=auto         # default — uses C++ when installed and strategy is eligible
make benchmark          # compare Python vs C++ throughput
```

C++ is used only for **simple DSL** (crossover/crossunder, no shorts). Everything else uses Python.

### Where to go deeper

| Topic | Document |
|-------|----------|
| Strategy DSL, Python, deployments | [docs/STRATEGY_GUIDE.md](docs/STRATEGY_GUIDE.md) |
| System architecture & implementation status | [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) |
| Every REST endpoint | [docs/architecture/API_OVERVIEW.md](docs/architecture/API_OVERVIEW.md) |
| Phase history | [docs/ROADMAP.md](docs/ROADMAP.md) |
| Production trading | [docs/LIVE_TRADING_RUNBOOK.md](docs/LIVE_TRADING_RUNBOOK.md) |

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
- **Long-only by default**; set `allow_short: true` in config to let SELL open short positions (BUY covers)
- View equity curve, trade list, Sharpe ratio, max drawdown (long/short breakdown when shorts enabled)
- Optional **C++ engine** for faster DSL backtests (`make build-cpp`; disabled when `allow_short` is on)

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

AlphaEdge supports three authentication modes:

| Client | Mechanism |
|--------|-----------|
| **Web SPA** | HTTP-only cookies (`alphaedge_access`, `alphaedge_refresh`) set on login/OAuth; browser sends `credentials: 'include'` |
| **API / scripts** | `Authorization: Bearer <access_token>` from login response (mobile clients receive token in body) |
| **Automation** | `X-API-Key: ae_live_...` with scoped permissions |

Cookie-based web sessions do not populate an in-memory JWT in the frontend; `/auth/me` and protected routes rely on cookies. Programmatic clients should use Bearer tokens or API keys.

**Rate limiting:** Tier resolution uses Bearer or API key headers. Cookie-only browser sessions fall back to IP-based anonymous tier limits.

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
- **Auth:** Bearer JWT, HTTP-only cookies (web), or `X-API-Key: ae_live_...`
- **Response shape:** `{ "data": { ... }, "meta": { "request_id": "..." } }`

### Major endpoint groups (63 routes)

| Group | Prefix | Examples |
|-------|--------|----------|
| Health | `/health/` | `live`, `ready` |
| Auth | `/auth/` | `register`, `login`, `me`, `oauth/{provider}`, `api-keys` |
| Instruments | `/instruments/` | list, bars, latest bar |
| Market data | `/market-data/` | `quotes`, `ingest` |
| Strategies | `/strategies/` | CRUD, versions, validate |
| Deployments | `/strategy-deployments/` | paper deploy, pause, resume |
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
| `ALPHA_VANTAGE_API_KEY` | Live quotes fallback (25 req/day free) | empty |
| `POLYGON_API_KEY` | **Preferred** ticker quotes (daily close on free tier) | empty |
| `QUOTE_PROVIDER` | `auto` (Polygon then AV), `polygon`, or `alpha_vantage` | `auto` |
| `GOOGLE_OAUTH_CLIENT_ID/SECRET` | Google login | empty |
| `GITHUB_OAUTH_CLIENT_ID/SECRET` | GitHub login | empty |
| `OAUTH_REDIRECT_BASE_URL` | Backend OAuth callback base | `http://localhost:8000/api/v1/auth/oauth` |
| `OAUTH_FRONTEND_CALLBACK_URL` | Post-login frontend URL | `http://localhost:5173/oauth/callback` |
| `ALPACA_API_KEY/SECRET` | Broker execution | empty |
| `OPENAI_API_KEY` | OpenAI API key for AI insights | required when `LLM_PROVIDER=openai` |
| `LLM_PROVIDER` | Insight generator: `openai` (ChatGPT) or `mock` (offline) | `openai` |
| `OPENAI_MODEL` | ChatGPT model for insights (e.g. `gpt-4o-mini`, `gpt-4o`) | `gpt-4o-mini` |
| `RATE_LIMIT_ENABLED` | API rate limiting | `true` (set `false` for local e2e) |
| `LIVE_TRADING_ENABLED` | Allow live (non-paper) orders | `false` |
| `CPP_ENGINE` | C++ backtest: `auto` / `off` / `require` | `auto` |

---

## Capability matrix

| Capability | Status |
|------------|--------|
| Paper Trading | Production Ready |
| Alpaca Integration | Supported (manual orders when `LIVE_TRADING_ENABLED=true`) |
| DSL Strategies | Production Ready |
| Python Strategies | Supported (trusted execution only — see [Strategy guide](docs/STRATEGY_GUIDE.md)) |
| Strategy Deployments (paper) | Production Ready |
| Backtesting | Production Ready |
| Optimization (grid, walk-forward, Bayesian) | Supported |
| AI Insights (OpenAI) | Supported (`LLM_PROVIDER=mock` for offline) |
| Marketplace (listings, clone) | Supported |
| Organizations & Collaboration | Supported |
| Live Trading (manual) | Experimental — requires checklist + `LIVE_TRADING_ENABLED` |
| Live Auto-Trading | Not Implemented — deployments require paper broker |
| IBKR / Zerodha / Angel One / Upstox | Stub adapters only (not enabled) |
| Crypto (Binance / Coinbase) | Not Implemented |
| Options | Not Implemented |
| Indian Markets | Planned (mock data provider exists) |
| Kill Switch | Not Implemented |
| Multi-tenant Strategy Sandbox | Not Implemented |

---

## Known limitations

AlphaEdge is a full research terminal, but not every architecture diagram feature is wired end-to-end yet. Read [docs/STRATEGY_GUIDE.md](docs/STRATEGY_GUIDE.md) for the strategy authoring reference.

| Area | What works today | Gap |
|------|------------------|-----|
| **DSL backtests** | Crossover, comparisons, `all`/`any`, stop/take-profit metadata | C++ engine only supports crossover/crossunder |
| **Python backtests** | `StrategyBase` sandbox, indicators via `context` | No C++ acceleration |
| **Short selling** | `allow_short: true` in backtest config | Not applied to paper deployments |
| **HOLD signals** | Ignored in backtests | Recorded in paper deployments (logged, no order) |
| **Paper deploy** | Bar ingestion → signal → paper order (with risk gate) | Paper broker only; no strategy-driven live execution |
| **Risk gate** | Pre-trade checks: cash/MIS margin, position size, portfolio exposure, daily loss | No real-time price feed — uses latest daily bar close as estimated fill price |
| **Live trading** | Manual orders via Alpaca when enabled | No strategy-driven live execution; set `LIVE_TRADING_ENABLED=true` after completing `docs/PRODUCTION_CHECKLIST.md` |
| **Market data** | Seed mock bars + optional Polygon/AV | Production-scale ingestion is bring-your-own keys |
| **Domain events** | Celery tasks + direct calls | Full outbox/event-bus pattern not everywhere |

Phase 14 (v1.0.0) and Phase 15 polish (v1.1.0) complete. See [docs/ROADMAP.md](docs/ROADMAP.md), [RELEASE_NOTES.md](RELEASE_NOTES.md), and [docs/ENGINEERING_AUDIT_V1.md](docs/ENGINEERING_AUDIT_V1.md) for audit details and honest capability status.

---

## Common issues

| Symptom | Fix |
|---------|-----|
| `database: error` on `/health/ready` | Start Docker Postgres: `docker compose -f infrastructure/docker-compose.yml up -d postgres redis` |
| Backtest stuck on `queued` | Start Celery worker (see Quick start) |
| OAuth redirects back to login | Ensure OAuth callback URLs match exactly; restart API after `.env` changes |
| Google "Access blocked" | Add your email as a test user in Google Cloud Console |
| GitHub `redirect_uri_mismatch` | Callback must be `http://localhost:8000/api/v1/auth/oauth/github/callback` |
| Stale AAPL price on home page | Set `POLYGON_API_KEY` (preferred) or `ALPHA_VANTAGE_API_KEY`; free AV is 25 req/day. ⏱ = DB fallback. |
| AI insight echoes the prompt / looks like a template | Old report — request a new insight; restart API so dev runs updated code in-process |
| AI insight fails / "OPENAI_API_KEY is required" | Set `OPENAI_API_KEY` in `.env` and restart API; or use `LLM_PROVIDER=mock` for offline mode |
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
| `make lint` | Ruff format + lint on backend |
| `make lint-types` | mypy on `src/` (local gradual typing — not CI-gated) |
| `make check` | Ruff + unit tests (mirrors CI lint + unit) |

---

## Further reading

| Document | Description |
|----------|-------------|
| [Case study](docs/CASE_STUDY.md) | Portfolio one-pager for recruiters |
| [Interview talking points](docs/INTERVIEW_TALKING_POINTS.md) | System-design interview prep |
| [Strategy guide](docs/STRATEGY_GUIDE.md) | DSL, Python runtime, deployments, backtest config |
| [Engineering audit (v1.0)](docs/ENGINEERING_AUDIT_V1.md) | Repository audit, security, performance, technical debt |
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
| Brokers | Paper simulator, Alpaca (live when enabled); IBKR/Indian/crypto stubs not production-ready |

---

## License

Proprietary — All rights reserved.
