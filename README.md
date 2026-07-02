# AlphaEdge

**Developer-first quantitative trading research and execution platform.**

AlphaEdge is not a trading dashboard. It is a production-grade platform for traders, quants, and researchers to design strategies, backtest at scale, manage risk, paper trade, and deploy to production.

## Status

**Phase 4 — Backtesting Engine** ✅ Complete

Event-driven backtest engine with DSL strategy execution, slippage/commission simulation, position sizing, partial fills, Celery job queue, results API, and CLI runner.

**Next:** Phase 5 — Portfolio & Risk (awaiting approval)

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture/ARCHITECTURE.md) | System design, bounded contexts, patterns, data flows |
| [Repository Structure](docs/architecture/REPOSITORY_STRUCTURE.md) | Monorepo layout and module conventions |
| [Database Design](docs/architecture/DATABASE_SCHEMA.md) | Conceptual schema and entity relationships |
| [API Design](docs/architecture/API_OVERVIEW.md) | REST conventions, versioning, module endpoints |
| [Development Roadmap](docs/ROADMAP.md) | Phased delivery plan with approval gates |

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Backend | Python, FastAPI, PostgreSQL, Redis, Celery, SQLAlchemy, Pydantic |
| Performance | C++, NumPy, Polars |
| Frontend | React, TypeScript, Tailwind CSS |
| Infrastructure | Docker, Docker Compose, GitHub Actions, Prometheus, Grafana |
| Deployment | AWS, Nginx (Kubernetes later) |

## Principles

- Clean Architecture + Domain-Driven Design
- Modular monolith (microservice-ready boundaries)
- Event-driven where it adds value
- CQRS for read-heavy analytics paths
- Repository pattern for persistence abstraction
- OpenAPI-first REST APIs

## Testing

```bash
# Unit tests only (no Docker required)
make test-unit

# Full suite — integration tests skip if Postgres is unavailable
make test

# Integration tests with Docker Postgres + Redis
make test-integration

# Integration tests when Postgres/Redis already running locally
make test-integration-local

# Mock-mode smoke test (no Docker, no API keys)
cd backend && python -m scripts.mock_smoke_test
```

Integration tests cover auth, market data ingestion, strategy CRUD, and full backtest execution against Postgres. CI runs them automatically with service containers.

## C++ Backtest Acceleration (optional)

The DSL backtest hot path can run on a pybind11 C++ extension (~60x faster, 1M events in ~0.1s):

```bash
# Build and install the extension (requires a C++17 compiler)
make build-cpp

# Compare Python vs C++ engine performance
make benchmark
```

When installed, DSL backtests use it automatically. Control via the `CPP_ENGINE` setting: `auto` (default), `off`, or `require`.

## License

Proprietary — All rights reserved.
