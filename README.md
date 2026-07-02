# AlphaEdge

**Developer-first quantitative trading research and execution platform.**

AlphaEdge is not a trading dashboard. It is a production-grade platform for traders, quants, and researchers to design strategies, backtest at scale, manage risk, paper trade, and deploy to production.

## Status

**Phase 1 — Foundation & Identity** ✅ Complete

Runnable FastAPI backend with Docker Compose, JWT authentication, RBAC, health checks, and CI pipeline.

**Next:** Phase 2 — Market Data (awaiting approval)

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

## License

Proprietary — All rights reserved.
