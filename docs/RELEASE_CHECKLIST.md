# Release Checklist

Use this checklist before tagging and releasing a new version.

## Code quality

- [ ] All CI checks pass (backend lint, type check, security audit, tests)
- [ ] All CI checks pass (frontend lint, security audit, build)
- [ ] No unresolved merge conflicts
- [ ] `CHANGELOG.md` updated with all changes since last release
- [ ] Version bumped in `backend/pyproject.toml`, `frontend/package.json`, `main.py` FastAPI version

## Testing

- [ ] Unit tests pass: `make test-unit`
- [ ] Integration tests pass: `make test-integration-local`
- [ ] E2e tests pass against staging: `make test-e2e`
- [ ] Frontend Playwright tests pass: `cd frontend && npx playwright test`
- [ ] Manual smoke test: register → create strategy → backtest → place paper order
- [ ] Risk gate verified: order with insufficient cash is rejected with `RISK_REJECTED`

## Security

- [ ] `pip-audit` reports no high/critical vulnerabilities
- [ ] `npm audit --audit-level=high` reports no issues
- [ ] No secrets committed to repository (`git log --all --oneline | xargs git show | grep -i secret`)
- [ ] `SECURITY_AUDIT.md` reviewed and updated if needed
- [ ] Production secrets rotated if any were exposed

## Infrastructure

- [ ] `python scripts/validate_env.py --prod` passes for staging environment
- [ ] Alembic migrations applied to staging: `alembic upgrade head`
- [ ] Rollback procedure tested on staging
- [ ] Health check endpoints return 200: `/api/v1/health/live` and `/api/v1/health/ready`

## Documentation

- [ ] `RELEASE_NOTES.md` written or updated
- [ ] `README.md` known limitations section is accurate
- [ ] `docs/ROADMAP.md` updated to mark completed phase
- [ ] API docs reviewed (`/api/v1/docs` on staging)

## Release

- [ ] Git tag created: `git tag -a v1.0.0 -m "Release v1.0.0"`
- [ ] Tag pushed: `git push origin v1.0.0`
- [ ] GitHub Release created with release notes attached
- [ ] Production deployment triggered
- [ ] Post-deployment smoke test on production

## Post-release

- [ ] Monitoring dashboards show healthy metrics (error rate, latency, risk rejections)
- [ ] On-call rotation updated
- [ ] Next phase / iteration planned in `docs/ROADMAP.md`
