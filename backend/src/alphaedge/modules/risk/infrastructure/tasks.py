import asyncio
from uuid import UUID

from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="risk.compute_portfolio_risk")
def compute_portfolio_risk_task(portfolio_id: str, user_id: str) -> None:
    asyncio.run(_compute_risk(UUID(portfolio_id), UUID(user_id)))


@celery_app.task(name="risk.compute_all_portfolio_risks")
def compute_all_portfolio_risks_task() -> None:
    asyncio.run(_compute_all_risks())


async def _compute_all_risks() -> None:
    from sqlalchemy import select

    from alphaedge.modules.portfolio.infrastructure.models import PortfolioModel
    from alphaedge.shared.infrastructure.database import async_session_factory

    async with async_session_factory() as session:
        result = await session.execute(select(PortfolioModel.id, PortfolioModel.user_id))
        rows = result.all()
    for portfolio_id, user_id in rows:
        await _compute_risk(portfolio_id, user_id)


async def _compute_risk(portfolio_id: UUID, user_id: UUID) -> None:
    from alphaedge.modules.portfolio.infrastructure.models import (
        SQLAlchemyHoldingRepository,
        SQLAlchemyPortfolioRepository,
    )
    from alphaedge.modules.risk.application.commands import ComputeRiskCommand
    from alphaedge.modules.risk.application.handlers import ComputeRiskHandler
    from alphaedge.modules.risk.infrastructure.models import (
        SQLAlchemyRiskLimitRepository,
        SQLAlchemyRiskSnapshotRepository,
    )
    from alphaedge.shared.infrastructure.database import async_session_factory

    async with async_session_factory() as session:
        handler = ComputeRiskHandler(
            SQLAlchemyPortfolioRepository(session),
            SQLAlchemyHoldingRepository(session),
            SQLAlchemyRiskSnapshotRepository(session),
            SQLAlchemyRiskLimitRepository(session),
            session,
        )
        await handler.handle(ComputeRiskCommand(user_id=user_id, portfolio_id=portfolio_id))
        await session.commit()
