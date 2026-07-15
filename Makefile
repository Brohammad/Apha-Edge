.PHONY: dev dev-down test test-unit test-integration lint migrate seed install build-cpp benchmark \
        frontend-dev frontend-build frontend-lint setup check ci-local demo demo-down prod prod-down prod-logs

# ── One-command bootstrap ────────────────────────────────────────────────────
setup: install build-cpp migrate
	@echo ""
	@echo "✓ Backend installed, C++ extension built, migrations applied."
	@echo "  Run 'make dev' to start the full stack, or 'make frontend-dev' for just the UI."

install:
	cd backend && pip install -e ".[dev]"

build-cpp:
	cd backend && pip install ./cpp

benchmark: build-cpp
	cd backend && python scripts/benchmark_backtest.py

dev:
	docker compose -f infrastructure/docker-compose.yml up --build

dev-down:
	docker compose -f infrastructure/docker-compose.yml down

test:
	cd backend && pytest -v --cov=alphaedge --cov-report=term-missing

test-unit:
	cd backend && pytest tests/unit -v

test-integration:
	docker compose -f infrastructure/docker-compose.yml up -d postgres redis
	@echo "Waiting for Postgres..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do \
		docker compose -f infrastructure/docker-compose.yml exec -T postgres pg_isready -U alphaedge >/dev/null 2>&1 && break; \
		sleep 1; \
	done
	cd backend && alembic upgrade head
	cd backend && pytest tests/integration -v -m integration

test-integration-local:
	cd backend && alembic upgrade head
	cd backend && pytest tests/integration -v -m integration

test-e2e:
	docker compose -f infrastructure/docker-compose.yml up -d postgres redis
	@echo "Waiting for Postgres..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do \
		docker compose -f infrastructure/docker-compose.yml exec -T postgres pg_isready -U alphaedge >/dev/null 2>&1 && break; \
		sleep 1; \
	done
	cd backend && alembic upgrade head
	@echo "Ensure API is running with RATE_LIMIT_ENABLED=false (e2e makes many requests)"
	cd backend && RATE_LIMIT_ENABLED=false pytest tests/e2e -v -m e2e

# ── Quality gates ────────────────────────────────────────────────────────────

# Fast local check: lint + unit tests (no DB required)
check: lint test-unit

lint:
	cd backend && ruff check src tests && ruff format --check src tests

lint-types:
	cd backend && mypy src

frontend-lint:
	cd frontend && npm run lint

frontend-e2e:
	cd frontend && npm run test:e2e

# Mirror what CI runs (requires Postgres + Redis running)
ci-local: lint test-unit test-integration
	@echo "✓ CI-local complete (lint + unit + integration)"

migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && (test -x .venv/bin/python && .venv/bin/python || python3) -m scripts.seed_data

demo:
	@test -f .env.demo || cp .env.demo.example .env.demo
	docker compose -p alphaedge-demo -f infrastructure/docker-compose.demo.yml --env-file .env.demo up --build -d
	@echo "Waiting for API to become healthy..."
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do \
		curl -sf http://localhost:8080/api/v1/health/live >/dev/null 2>&1 && break; \
		sleep 2; \
	done
	@docker compose -p alphaedge-demo -f infrastructure/docker-compose.demo.yml restart gateway >/dev/null 2>&1 || true
	@echo ""
	@echo "✓ Demo stack starting on http://localhost:8080"
	@echo "  Login: demo@example.com / DemoAlphaEdge1!"
	@echo "  See docs/DEMO_DEPLOY.md"

demo-down:
	docker compose -p alphaedge-demo -f infrastructure/docker-compose.demo.yml --env-file .env.demo down

prod:
	@test -f .env.prod || (echo "Copy .env.prod.example → .env.prod and set secrets first" && exit 1)
	docker compose -p alphaedge-prod -f infrastructure/docker-compose.prod.yml --env-file .env.prod up --build -d
	@echo ""
	@echo "✓ Production stack starting — https://alphaedge.brohammad.tech (after DNS propagates)"
	@echo "  Login: demo@example.com / DemoAlphaEdge1!"
	@echo "  See docs/DEPLOY_HOSTINGER.md"

prod-down:
	docker compose -p alphaedge-prod -f infrastructure/docker-compose.prod.yml --env-file .env.prod down

prod-logs:
	docker compose -p alphaedge-prod -f infrastructure/docker-compose.prod.yml logs -f api

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

load-test:
	cd backend && python scripts/load_test.py --base-url http://localhost:8000
