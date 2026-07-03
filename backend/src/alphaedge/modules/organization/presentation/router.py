from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.organization.application.commands import (
    CreateOrganizationCommand,
    ListOrganizationsQuery,
)
from alphaedge.modules.organization.application.handlers import (
    CreateOrganizationHandler,
    ListOrganizationsHandler,
)
from alphaedge.modules.organization.infrastructure.models import (
    SQLAlchemyOrganizationMemberRepository,
    SQLAlchemyOrganizationRepository,
)
from alphaedge.shared.presentation.envelope import success_response

organizations_router = APIRouter(prefix="/organizations", tags=["Organizations"])


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100)


@organizations_router.post("", status_code=201)
async def create_organization(
    body: CreateOrganizationRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    handler = CreateOrganizationHandler(org_repo, member_repo)
    result = await handler.handle(
        CreateOrganizationCommand(user_id=user_id, name=body.name, slug=body.slug)
    )
    return success_response(
        {
            "id": str(result.id),
            "name": result.name,
            "slug": result.slug,
            "owner_id": str(result.owner_id),
            "plan_tier": result.plan_tier,
            "created_at": result.created_at,
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@organizations_router.get("")
async def list_organizations(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    handler = ListOrganizationsHandler(org_repo)
    items = await handler.handle(ListOrganizationsQuery(user_id=user_id))
    return success_response(
        {
            "items": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "slug": o.slug,
                    "owner_id": str(o.owner_id),
                    "plan_tier": o.plan_tier,
                    "created_at": o.created_at,
                }
                for o in items
            ]
        },
        request_id=getattr(request.state, "request_id", ""),
    )
