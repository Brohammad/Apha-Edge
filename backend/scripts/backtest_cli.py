#!/usr/bin/env python3
"""CLI backtest runner — executes a backtest synchronously without Celery."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from uuid import UUID

from alphaedge.modules.backtesting.application.commands import SubmitBacktestCommand
from alphaedge.modules.backtesting.application.handlers import SubmitBacktestHandler
from alphaedge.modules.backtesting.infrastructure.models import SQLAlchemyBacktestRunRepository
from alphaedge.modules.backtesting.infrastructure.runner import execute_backtest
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.shared.infrastructure.database import async_session_factory


async def _submit(user_id: UUID, version_id: UUID, name: str, config: dict) -> UUID:
    async with async_session_factory() as session:
        run_repo = SQLAlchemyBacktestRunRepository(session)
        strategy_repo = SQLAlchemyStrategyRepository(session)
        version_repo = SQLAlchemyStrategyVersionRepository(session)
        handler = SubmitBacktestHandler(run_repo, strategy_repo, version_repo)
        result = await handler.handle(
            SubmitBacktestCommand(
                user_id=user_id,
                strategy_version_id=version_id,
                name=name,
                config=config,
            )
        )
        await session.commit()
        return result.id


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a backtest synchronously")
    parser.add_argument("--user-id", required=True, help="Owner user UUID")
    parser.add_argument("--strategy-version-id", required=True, help="Validated strategy version UUID")
    parser.add_argument("--name", default="CLI Backtest", help="Backtest run name")
    parser.add_argument(
        "--config",
        required=True,
        help="Backtest config as JSON string or path to JSON file",
    )
    args = parser.parse_args()

    config_raw = args.config
    if config_raw.endswith(".json"):
        with open(config_raw) as f:
            config = json.load(f)
    else:
        config = json.loads(config_raw)

    try:
        run_id = asyncio.run(
            _submit(UUID(args.user_id), UUID(args.strategy_version_id), args.name, config)
        )
        print(f"Submitted backtest run: {run_id}")
        asyncio.run(execute_backtest(run_id))
        print(f"Backtest completed: {run_id}")
        return 0
    except Exception as exc:
        print(f"Backtest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
