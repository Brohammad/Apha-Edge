import asyncio
from uuid import UUID

from alphaedge.shared.infrastructure.celery_app import celery_app


@celery_app.task(name="risk.compute_portfolio_risk")
def compute_portfolio_risk_task(portfolio_id: str, user_id: str) -> None:
    asyncio.run(_compute_risk(UUID(portfolio_id), UUID(user_id)))


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
