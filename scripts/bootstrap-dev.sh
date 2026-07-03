#!/usr/bin/env bash
# AlphaEdge local bootstrap — run from repository root
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop and retry."
  exit 1
fi

cp -n .env.example .env 2>/dev/null || true
echo ">>> Ensure .env has APP_SECRET_KEY and JWT_SECRET_KEY set."

docker compose -f infrastructure/docker-compose.yml up -d postgres redis

make install
make migrate
make seed

cat <<'EOF'

AlphaEdge bootstrap complete.

Open THREE terminals:

  Terminal A — API:
    cd backend && source .venv/bin/activate
    RATE_LIMIT_ENABLED=false uvicorn alphaedge.main:app --host 127.0.0.1 --port 8000 --reload

  Terminal B — Celery (required for backtests & orders):
    cd backend && source .venv/bin/activate
    celery -A alphaedge.shared.infrastructure.celery_app worker --loglevel=info

  Terminal C — Frontend:
    make frontend-dev
    → http://localhost:5173

Health: curl -s http://localhost:8000/api/v1/health/ready

See README.md "Complete project guide" for the full API demo script.

EOF
