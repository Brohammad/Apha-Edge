from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.strategy.application.commands import (
    CreateStrategyCommand,
    CreateStrategyVersionCommand,
    DeleteStrategyCommand,
    GetStrategyQuery,
    GetStrategyVersionQuery,
    ListIndicatorsQuery,
    ListStrategiesQuery,
    ListStrategyVersionsQuery,
    UpdateStrategyCommand,
    ValidateStrategyVersionCommand,
)
from alphaedge.modules.strategy.application.handlers import (
    CreateStrategyHandler,
    CreateStrategyVersionHandler,
    DeleteStrategyHandler,
    GetStrategyHandler,
    GetStrategyVersionHandler,
    ListIndicatorsHandler,
    ListStrategiesHandler,
    ListStrategyVersionsHandler,
    UpdateStrategyHandler,
    ValidateStrategyVersionHandler,
)
from alphaedge.modules.strategy.domain.enums import StrategyType
from alphaedge.modules.strategy.domain.templates import get_template, list_templates
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyIndicatorRepository,
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.modules.strategy.presentation.schemas import (
    CreateStrategyRequest,
    CreateStrategyVersionRequest,
    IndicatorResponse,
    StrategyResponse,
    StrategyVersionResponse,
    UpdateStrategyRequest,
    ValidationResultResponse,
)
from alphaedge.shared.presentation.envelope import success_response

strategies_router = APIRouter(prefix="/strategies", tags=["Strategy"])
indicators_router = APIRouter(prefix="/indicators", tags=["Strategy"])


def _repos(session: AsyncSession):
    return (
        SQLAlchemyStrategyRepository(session),
        SQLAlchemyStrategyVersionRepository(session),
        SQLAlchemyIndicatorRepository(session),
    )


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def _to_strategy(dto: object) -> dict:
    return StrategyResponse(
        id=str(dto.id),
        user_id=str(dto.user_id),
        name=dto.name,
        description=dto.description,
        strategy_type=dto.strategy_type,
        is_active=dto.is_active,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    ).model_dump(mode="json")


def _to_version(dto: object) -> dict:
    return StrategyVersionResponse(
        id=str(dto.id),
        strategy_id=str(dto.strategy_id),
        version=dto.version,
        source_code=dto.source_code,
        parameters=dto.parameters,
        compiled_hash=dto.compiled_hash,
        status=dto.status,
        created_at=dto.created_at,
    ).model_dump(mode="json")


def _to_indicator(dto: object) -> dict:
    return IndicatorResponse(
        id=str(dto.id),
        name=dto.name,
        category=dto.category,
        parameters_schema=dto.parameters_schema,
        implementation=dto.implementation,
    ).model_dump(mode="json")


@strategies_router.get("")
async def list_strategies(
    request: Request,
    active_only: bool = True,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, _, _ = _repos(session)
    handler = ListStrategiesHandler(strategy_repo)
    items, total = await handler.handle(
        ListStrategiesQuery(user_id=user_id, active_only=active_only, limit=limit, offset=offset)
    )
    return success_response(
        {"items": [_to_strategy(s) for s in items], "total_count": total},
        request_id=_request_id(request),
    )


@strategies_router.post("", status_code=status.HTTP_201_CREATED)
async def create_strategy(
    body: CreateStrategyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, version_repo, _ = _repos(session)
    handler = CreateStrategyHandler(strategy_repo, version_repo)
    result = await handler.handle(
        CreateStrategyCommand(
            user_id=user_id,
            name=body.name,
            strategy_type=StrategyType(body.strategy_type),
            description=body.description,
            source_code=body.source_code,
            parameters=body.parameters,
        )
    )
    return success_response(_to_strategy(result), request_id=_request_id(request))


@strategies_router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, _, _ = _repos(session)
    handler = GetStrategyHandler(strategy_repo)
    result = await handler.handle(GetStrategyQuery(user_id=user_id, strategy_id=strategy_id))
    return success_response(_to_strategy(result), request_id=_request_id(request))


@strategies_router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: UUID,
    body: UpdateStrategyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, _, _ = _repos(session)
    handler = UpdateStrategyHandler(strategy_repo)
    result = await handler.handle(
        UpdateStrategyCommand(
            user_id=user_id,
            strategy_id=strategy_id,
            name=body.name,
            description=body.description,
            is_active=body.is_active,
        )
    )
    return success_response(_to_strategy(result), request_id=_request_id(request))


@strategies_router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, _, _ = _repos(session)
    handler = DeleteStrategyHandler(strategy_repo)
    await handler.handle(DeleteStrategyCommand(user_id=user_id, strategy_id=strategy_id))


@strategies_router.post("/{strategy_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_strategy_version(
    strategy_id: UUID,
    body: CreateStrategyVersionRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, version_repo, _ = _repos(session)
    handler = CreateStrategyVersionHandler(strategy_repo, version_repo)
    result = await handler.handle(
        CreateStrategyVersionCommand(
            user_id=user_id,
            strategy_id=strategy_id,
            source_code=body.source_code,
            parameters=body.parameters,
        )
    )
    return success_response(_to_version(result), request_id=_request_id(request))


@strategies_router.get("/{strategy_id}/versions")
async def list_strategy_versions(
    strategy_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, version_repo, _ = _repos(session)
    handler = ListStrategyVersionsHandler(strategy_repo, version_repo)
    items = await handler.handle(
        ListStrategyVersionsQuery(user_id=user_id, strategy_id=strategy_id)
    )
    return success_response(
        {"items": [_to_version(v) for v in items], "total_count": len(items)},
        request_id=_request_id(request),
    )


@strategies_router.get("/{strategy_id}/versions/{version_id}")
async def get_strategy_version(
    strategy_id: UUID,
    version_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, version_repo, _ = _repos(session)
    handler = GetStrategyVersionHandler(strategy_repo, version_repo)
    result = await handler.handle(
        GetStrategyVersionQuery(user_id=user_id, strategy_id=strategy_id, version_id=version_id)
    )
    return success_response(_to_version(result), request_id=_request_id(request))


@strategies_router.post("/{strategy_id}/versions/{version_id}/validate")
async def validate_strategy_version(
    strategy_id: UUID,
    version_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
):
    strategy_repo, version_repo, _ = _repos(session)
    handler = ValidateStrategyVersionHandler(strategy_repo, version_repo)
    result = await handler.handle(
        ValidateStrategyVersionCommand(
            user_id=user_id, strategy_id=strategy_id, version_id=version_id
        )
    )
    return success_response(
        ValidationResultResponse(
            version_id=str(result.version_id),
            status=result.status,
            compiled_hash=result.compiled_hash,
            errors=result.errors,
            error_lines=result.error_lines,
        ).model_dump(),
        request_id=_request_id(request),
    )


@indicators_router.get("")
async def list_indicators(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    _, _, indicator_repo = _repos(session)
    handler = ListIndicatorsHandler(indicator_repo)
    items = await handler.handle(ListIndicatorsQuery())
    return success_response(
        {"items": [_to_indicator(i) for i in items], "total_count": len(items)},
        request_id=_request_id(request),
    )


@strategies_router.get("/templates")
async def strategy_templates(request: Request, _user_id: UUID = Depends(get_current_user_id)):
    return success_response({"items": list_templates()}, request_id=_request_id(request))


@strategies_router.get("/templates/{template_id}")
async def strategy_template(
    template_id: str,
    request: Request,
    _user_id: UUID = Depends(get_current_user_id),
):
    tpl = get_template(template_id)
    if not tpl:
        from alphaedge.shared.domain.exceptions import NotFoundError
        raise NotFoundError("Template", template_id)
    return success_response({"id": template_id, **tpl}, request_id=_request_id(request))
