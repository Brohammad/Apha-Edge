from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.execution.infrastructure.models import SQLAlchemyBrokerConnectionRepository
from alphaedge.modules.portfolio.infrastructure.models import SQLAlchemyPortfolioRepository
from alphaedge.modules.strategy.application.deployment_handlers import (
    CreateDeploymentCommand,
    CreateDeploymentHandler,
    DeploymentDTO,
    ListDeploymentsHandler,
    ListDeploymentsQuery,
    PauseDeploymentCommand,
    PauseDeploymentHandler,
    ResumeDeploymentCommand,
    ResumeDeploymentHandler,
)
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyDeploymentRepository,
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.modules.strategy.presentation.schemas import (
    CreateDeploymentRequest,
    DeploymentResponse,
)
from alphaedge.shared.presentation.envelope import success_response

deployments_router = APIRouter(prefix="/strategy-deployments", tags=["Strategy Deployments"])


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_deployment(dto: DeploymentDTO) -> dict:
    return DeploymentResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        strategy_version_id=str(dto.strategy_version_id),
        portfolio_id=str(dto.portfolio_id),
        broker_connection_id=str(dto.broker_connection_id),
        instrument_ids=dto.instrument_ids,
        quantity=dto.quantity,
        is_active=dto.is_active,
        last_signal_at=dto.last_signal_at,
        last_signal_action=dto.last_signal_action,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


@deployments_router.get("")
async def list_deployments(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    repo = SQLAlchemyStrategyDeploymentRepository(session)
    handler = ListDeploymentsHandler(repo)
    items = await handler.handle(ListDeploymentsQuery(user_id=user_id))
    return success_response(
        {"items": [_to_deployment(i) for i in items], "total_count": len(items)},
        request_id=_request_id(request),
    )


@deployments_router.post("", status_code=status.HTTP_201_CREATED)
async def create_deployment(
    body: CreateDeploymentRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = CreateDeploymentHandler(
        SQLAlchemyStrategyDeploymentRepository(session),
        SQLAlchemyStrategyVersionRepository(session),
        SQLAlchemyStrategyRepository(session),
        SQLAlchemyPortfolioRepository(session),
        SQLAlchemyBrokerConnectionRepository(session),
    )
    result = await handler.handle(
        CreateDeploymentCommand(
            user_id=user_id,
            strategy_version_id=UUID(body.strategy_version_id),
            portfolio_id=UUID(body.portfolio_id),
            broker_connection_id=UUID(body.broker_connection_id),
            instrument_ids=[UUID(i) for i in body.instrument_ids],
            quantity=body.quantity,
        )
    )
    await session.commit()
    return success_response(_to_deployment(result), request_id=_request_id(request))


@deployments_router.post("/{deployment_id}/pause")
async def pause_deployment_route(
    deployment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = PauseDeploymentHandler(SQLAlchemyStrategyDeploymentRepository(session))
    result = await handler.handle(
        PauseDeploymentCommand(user_id=user_id, deployment_id=deployment_id)
    )
    await session.commit()
    return success_response(_to_deployment(result), request_id=_request_id(request))


@deployments_router.post("/{deployment_id}/resume")
async def resume_deployment_route(
    deployment_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    handler = ResumeDeploymentHandler(SQLAlchemyStrategyDeploymentRepository(session))
    result = await handler.handle(
        ResumeDeploymentCommand(user_id=user_id, deployment_id=deployment_id)
    )
    await session.commit()
    return success_response(_to_deployment(result), request_id=_request_id(request))
