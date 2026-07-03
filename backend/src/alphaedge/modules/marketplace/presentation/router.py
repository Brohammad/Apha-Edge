from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.marketplace.application.handlers import (
    CloneListingCommand,
    CloneListingHandler,
    ListPublicListingsHandler,
    PublishListingCommand,
    PublishListingHandler,
)
from alphaedge.modules.marketplace.infrastructure.models import SQLAlchemyStrategyListingRepository
from alphaedge.modules.organization.infrastructure.models import (
    SQLAlchemyOrganizationMemberRepository,
)
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.shared.presentation.envelope import success_response

marketplace_router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


class PublishListingRequest(BaseModel):
    strategy_id: str
    organization_id: str
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    price_cents: int = Field(default=0, ge=0)


@marketplace_router.get("/listings")
async def list_listings(
    request: Request,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    _user_id: UUID = Depends(get_current_user_id),
):
    repo = SQLAlchemyStrategyListingRepository(session)
    handler = ListPublicListingsHandler(repo)
    items = await handler.handle(limit=limit, offset=offset)
    return success_response(
        {
            "items": [
                {
                    "id": str(i.id),
                    "strategy_id": str(i.strategy_id),
                    "organization_id": str(i.organization_id),
                    "title": i.title,
                    "description": i.description,
                    "price_cents": i.price_cents,
                    "clone_count": i.clone_count,
                    "created_at": i.created_at,
                }
                for i in items
            ]
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@marketplace_router.post("/listings", status_code=201)
async def publish_listing(
    body: PublishListingRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    listing_repo = SQLAlchemyStrategyListingRepository(session)
    strategy_repo = SQLAlchemyStrategyRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    handler = PublishListingHandler(listing_repo, strategy_repo, member_repo)
    result = await handler.handle(
        PublishListingCommand(
            user_id=user_id,
            strategy_id=UUID(body.strategy_id),
            organization_id=UUID(body.organization_id),
            title=body.title,
            description=body.description,
            price_cents=body.price_cents,
        )
    )
    return success_response(
        {
            "id": str(result.id),
            "strategy_id": str(result.strategy_id),
            "title": result.title,
            "price_cents": result.price_cents,
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@marketplace_router.post("/listings/{listing_id}/clone", status_code=201)
async def clone_listing(
    listing_id: UUID,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    listing_repo = SQLAlchemyStrategyListingRepository(session)
    strategy_repo = SQLAlchemyStrategyRepository(session)
    version_repo = SQLAlchemyStrategyVersionRepository(session)
    handler = CloneListingHandler(listing_repo, strategy_repo, version_repo)
    result = await handler.handle(CloneListingCommand(user_id=user_id, listing_id=listing_id))
    return success_response(result, request_id=getattr(request.state, "request_id", ""))
