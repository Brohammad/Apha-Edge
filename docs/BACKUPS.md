# Database backup and restore drill

AlphaEdge stores durable state in PostgreSQL. Redis is ephemeral (rate limits,
kill-switch flag, caches, Celery broker). Back up Postgres regularly.

## What to back up

| Asset | Required | Notes |
|-------|----------|-------|
| PostgreSQL volume / dump | **Yes** | Users, strategies, portfolios, orders, bars |
| `.env.prod` secrets | **Yes** (offline) | Never commit; store in a password manager |
| Redis | Optional | Kill switch resets to off after restore unless re-set |
| Grafana / Prometheus | Optional | Observability only |

## Local / demo dump

```bash
# While demo or prod compose is running:
docker compose -p alphaedge-prod -f infrastructure/docker-compose.prod.yml \
  exec -T postgres pg_dump -U alphaedge alphaedge > backup-$(date +%Y%m%d).sql
```

## Restore drill (practice quarterly)

1. Stop the API/worker/beat (keep Postgres up, or restore into a fresh volume).
2. Restore:

```bash
cat backup-YYYYMMDD.sql | docker compose -p alphaedge-prod \
  -f infrastructure/docker-compose.prod.yml exec -T postgres \
  psql -U alphaedge -d alphaedge
```

3. Start the stack: `make prod`
4. Verify:
   - `curl -sf https://YOUR_HOST/api/v1/health/ready`
   - Login with a known user
   - Open a strategy and a portfolio
5. Re-check kill switch (`GET /api/v1/admin/kill-switch`) — Redis state is not in the SQL dump.

## Automation sketch (cron on VPS)

```bash
#!/usr/bin/env bash
set -euo pipefail
DIR=/var/backups/alphaedge
mkdir -p "$DIR"
docker compose -p alphaedge-prod -f /opt/alpha-edge/infrastructure/docker-compose.prod.yml \
  exec -T postgres pg_dump -U alphaedge alphaedge | gzip > "$DIR/alphaedge-$(date +%Y%m%d%H%M).sql.gz"
find "$DIR" -name '*.sql.gz' -mtime +14 -delete
```

## Success criteria for a drill

- [ ] Dump completes without error  
- [ ] Restore into a throwaway compose project succeeds  
- [ ] Health ready returns 200  
- [ ] Demo login works  
- [ ] Restore time measured and recorded  
