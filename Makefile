.PHONY: dev dev-down test lint migrate seed install

install:
	cd backend && pip install -e ".[dev]"

dev:
	docker compose -f infrastructure/docker-compose.yml up --build

dev-down:
	docker compose -f infrastructure/docker-compose.yml down

test:
	cd backend && pytest -v --cov=alphaedge --cov-report=term-missing

lint:
	cd backend && ruff check src tests && ruff format --check src tests && mypy src

migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && python -m scripts.seed_data
