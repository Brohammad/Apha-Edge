#!/bin/sh
set -e

cd /app
export PYTHONPATH=/app/src:/app
alembic upgrade head

if [ "${RUN_DEMO_SEED:-false}" = "true" ]; then
  python -m scripts.seed_data
  python -m scripts.seed_demo_user
fi

exec uvicorn alphaedge.main:app --host 0.0.0.0 --port 8000
