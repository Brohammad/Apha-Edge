.PHONY: dev dev-down test test-unit test-integration lint migrate seed install build-cpp benchmark frontend-dev frontend-build frontend-lint

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

lint:
	cd backend && ruff check src tests && ruff format --check src tests && mypy src

migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && python -m scripts.seed_data

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint
