# Organization RBAC

AlphaEdge organizations are **team desks** for marketplace publishing and shared workspace membership.
They are separate from platform identity roles (`admin` / `trader` / `viewer`).

## Roles

| Role | Capabilities |
|------|----------------|
| `owner` | Full control; created with the organization |
| `admin` | Invite/remove members, publish marketplace listings, change member roles (except owner) |
| `member` | Read org + member list; cannot publish or invite |

## Endpoints

| Method | Path | Min role |
|--------|------|----------|
| `POST` | `/organizations` | Authenticated user (becomes owner) |
| `GET` | `/organizations` | Authenticated (own memberships) |
| `GET` | `/organizations/{id}` | `member` |
| `GET` | `/organizations/{id}/members` | `member` |
| `POST` | `/organizations/{id}/members` | `admin` |
| `PATCH` | `/organizations/{id}/members/{user_id}` | `admin` |
| `DELETE` | `/organizations/{id}/members/{user_id}` | `admin` |
| `POST` | `/marketplace/listings` | Org `admin` + strategy owner; **DSL only** |

## Notes

- Portfolio, strategy, backtest, and order routes remain **user-owned** (not org-scoped).
- Platform `require_permission()` is available for identity RBAC but org routes use `require_org_role`.
- Python strategies cannot be marketplace-published until multi-tenant isolation lands (`docs/STRATEGY_SANDBOX.md`).
