# Strategy execution sandbox

AlphaEdge runs **user-authored Python strategies** inside the backtest/worker process.
This document describes the current (trusted single-tenant) controls and the migration
path for multi-tenant marketplace execution.

## Trust model (today)

| Boundary | Status |
|----------|--------|
| AST import allowlist | Enforced (`alphaedge.modules.strategy.domain.*` only) |
| Restricted builtins | Enforced (no `open`, `eval`, unrestricted `__import__`) |
| Wall-clock timeout | Enforced (`STRATEGY_EXEC_TIMEOUT_SECONDS`, `STRATEGY_LOAD_TIMEOUT_SECONDS`) |
| Memory soft limit | Best-effort via `RLIMIT_AS` (`STRATEGY_MEMORY_LIMIT_MB`) |
| Network isolation | **Not enforced in-process** — treat authors as trusted |
| Filesystem isolation | **Not enforced** |
| Marketplace Python publish | **Blocked** until container isolation ships |
| DSL strategies | Safe declarative runtime — preferred for sharing |

Python strategies are appropriate for **private research by the account owner**.
They are **not** safe to execute untrusted third-party code on a shared host.

## Configuration

| Env var | Default | Meaning |
|---------|---------|---------|
| `STRATEGY_LOAD_TIMEOUT_SECONDS` | `10` | Max seconds to compile/load strategy source |
| `STRATEGY_EXEC_TIMEOUT_SECONDS` | `5` | Max seconds per `on_init` / `on_bar` call |
| `STRATEGY_MEMORY_LIMIT_MB` | `512` | Soft address-space ceiling when OS supports it |

## Multi-tenant migration path (not implemented)

When marketplace Python strategies are required:

1. Extract a `strategy-runner` worker that accepts a sealed job (source hash + bars).
2. Execute each job in a short-lived container or Firecracker microVM with:
   - no network egress
   - read-only root filesystem
   - cgroup CPU + memory limits
   - seccomp / dropped capabilities
   - hard wall-clock kill
3. Return signals/metrics over a narrow IPC channel; never load user code in the API process.
4. Re-enable marketplace Python publish behind that runner.

Until then, marketplace listings accept **DSL only**.

## Operator guidance

- Run Celery workers as a non-root user.
- Prefer DSL for any strategy that may be cloned or shared.
- Keep `LIVE_TRADING_ENABLED=false` unless credentials encryption and kill switch are verified.
