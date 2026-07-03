# AlphaEdge AWS Deployment

Production stack on AWS using ECS Fargate, RDS PostgreSQL, and ElastiCache Redis.

## Architecture

```
Internet → ALB → ECS (api + worker services) → RDS Postgres
                              ↘ ElastiCache Redis
```

## Prerequisites

- AWS CLI configured
- Terraform >= 1.5
- Docker images pushed to ECR

## Quick start

```bash
cd infrastructure/aws/terraform
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars
```

## Services

| Service | Image | Port |
|---------|-------|------|
| `alphaedge-api` | `alphaedge-api:latest` | 8000 |
| `alphaedge-worker` | `alphaedge-worker:latest` | — |
| `alphaedge-frontend` | `alphaedge-frontend:latest` | 80 |

## Environment variables (ECS task)

Set via AWS Secrets Manager or SSM Parameter Store:

- `DATABASE_URL` — RDS connection string
- `REDIS_URL` / `CELERY_BROKER_URL` — ElastiCache endpoints
- `JWT_SECRET_KEY`, `APP_SECRET_KEY`
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`
- `ALPACA_API_KEY`, `ALPACA_API_SECRET`

## Monitoring

Import Grafana dashboard from `infrastructure/grafana/dashboards/alphaedge-api.json`.
Prometheus scrapes `/api/v1/metrics` via ECS service discovery or sidecar.
