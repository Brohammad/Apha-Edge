"""Evaluate active strategy deployments when new bars arrive."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.execution.application.commands import SubmitOrderCommand
from alphaedge.modules.execution.application.handlers import SubmitOrderHandler
from alphaedge.modules.execution.domain.enums import OrderType
from alphaedge.modules.execution.infrastructure.models import (
    SQLAlchemyBrokerConnectionRepository,
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderEventRepository,
    SQLAlchemyOrderRepository,
)
from alphaedge.modules.execution.infrastructure.tasks import process_order_task
from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyInstrumentRepository
from alphaedge.modules.portfolio.infrastructure.models import SQLAlchemyPortfolioRepository
from alphaedge.modules.strategy.domain.deployment import StrategyDeployment
from alphaedge.modules.strategy.domain.enums import SignalAction, VersionStatus
from alphaedge.modules.strategy.domain.runtime import clear_runtime, get_runtime
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyDeploymentRepository,
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.shared.domain.value_objects import Side
from alphaedge.shared.infrastructure.database import async_session_factory


async def evaluate_deployments_for_bar(bar: Bar) -> int:
    """Run all active deployments watching this instrument; return orders submitted."""
    orders_submitted = 0
    async with async_session_factory() as session:
        dep_repo = SQLAlchemyStrategyDeploymentRepository(session)
        deployments = await dep_repo.list_active_for_instrument(bar.instrument_id)
        if not deployments:
            return 0

        strategy_repo = SQLAlchemyStrategyRepository(session)
        version_repo = SQLAlchemyStrategyVersionRepository(session)
        order_repo = SQLAlchemyOrderRepository(session)
        connection_repo = SQLAlchemyBrokerConnectionRepository(session)
        portfolio_repo = SQLAlchemyPortfolioRepository(session)
        instrument_repo = SQLAlchemyInstrumentRepository(session)
        event_repo = SQLAlchemyOrderEventRepository(session)
        execution_repo = SQLAlchemyExecutionRepository(session)
        _ = execution_repo  # reserved for future audit

        submit_handler = SubmitOrderHandler(
            order_repo, connection_repo, portfolio_repo, instrument_repo, event_repo
        )

        for deployment in deployments:
            if bar.instrument_id not in deployment.instrument_ids:
                continue
            submitted = await _evaluate_deployment(
                session,
                deployment,
                bar,
                strategy_repo,
                version_repo,
                submit_handler,
            )
            orders_submitted += submitted

        await session.commit()
    return orders_submitted


async def _evaluate_deployment(
    session,
    deployment: StrategyDeployment,
    bar: Bar,
    strategy_repo,
    version_repo,
    submit_handler: SubmitOrderHandler,
) -> int:
    version = await version_repo.get_by_id(deployment.strategy_version_id)
    if not version or version.status != VersionStatus.VALIDATED:
        return 0
    strategy = await strategy_repo.get_by_id(version.strategy_id)
    if not strategy:
        return 0

    cache_key = str(deployment.id)
    runtime = get_runtime(
        cache_key,
        strategy.strategy_type,
        version.source_code,
        strategy.name,
        version.parameters,
    )
    signal = runtime.on_bar(bar)
    if not signal or signal.action == SignalAction.HOLD:
        return 0

    side = Side.BUY if signal.action == SignalAction.BUY else Side.SELL
    idempotency_key = (
        f"deploy:{deployment.id}:{bar.instrument_id}:{bar.timestamp.isoformat()}:{side.value}"
    )
    order_dto = await submit_handler.handle(
        SubmitOrderCommand(
            user_id=deployment.user_id,
            portfolio_id=deployment.portfolio_id,
            broker_connection_id=deployment.broker_connection_id,
            instrument_id=bar.instrument_id,
            side=side.value,
            order_type=OrderType.MARKET.value,
            quantity=str(deployment.quantity),
            idempotency_key=idempotency_key,
        )
    )
    deployment.record_signal(signal.action.value, bar.timestamp)
    dep_repo = SQLAlchemyStrategyDeploymentRepository(session)
    await dep_repo.save(deployment)
    process_order_task.delay(str(order_dto.id))
    return 1


async def pause_deployment(deployment_id: UUID) -> None:
    clear_runtime(str(deployment_id))


def evaluate_deployments_for_bar_sync(bar: Bar) -> int:
    import asyncio

    return asyncio.run(evaluate_deployments_for_bar(bar))
