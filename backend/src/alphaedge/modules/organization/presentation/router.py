from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.organization.application.authz import get_org_or_404, require_org_role
from alphaedge.modules.organization.application.commands import (
    CreateOrganizationCommand,
    ListOrganizationsQuery,
)
from alphaedge.modules.organization.application.handlers import (
    CreateOrganizationHandler,
    ListOrganizationsHandler,
)
from alphaedge.modules.organization.domain.entities import OrganizationMember
from alphaedge.modules.organization.domain.enums import OrgRole
from alphaedge.modules.organization.infrastructure.models import (
    SQLAlchemyOrganizationMemberRepository,
    SQLAlchemyOrganizationRepository,
)
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError
from alphaedge.shared.presentation.envelope import success_response

organizations_router = APIRouter(prefix="/organizations", tags=["Organizations"])


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100)


class AddMemberRequest(BaseModel):
    user_id: str
    role: OrgRole = OrgRole.MEMBER


class UpdateMemberRoleRequest(BaseModel):
    role: OrgRole


def _member_payload(m: OrganizationMember) -> dict:
    return {
        "organization_id": str(m.organization_id),
        "user_id": str(m.user_id),
        "role": m.role.value,
        "joined_at": m.joined_at.isoformat(),
    }


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


@organizations_router.get("/{org_id}")
async def get_organization(
    org_id: UUID,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    org = await get_org_or_404(org_repo, org_id)
    member = await require_org_role(
        member_repo, org_id=org_id, user_id=user_id, min_role=OrgRole.MEMBER
    )
    return success_response(
        {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "owner_id": str(org.owner_id),
            "plan_tier": org.plan_tier,
            "created_at": org.created_at,
            "your_role": member.role.value,
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@organizations_router.get("/{org_id}/members")
async def list_members(
    org_id: UUID,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    await get_org_or_404(org_repo, org_id)
    await require_org_role(member_repo, org_id=org_id, user_id=user_id, min_role=OrgRole.MEMBER)
    members = await member_repo.list_members(org_id)
    return success_response(
        {"items": [_member_payload(m) for m in members]},
        request_id=getattr(request.state, "request_id", ""),
    )


@organizations_router.post("/{org_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: UUID,
    body: AddMemberRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    await get_org_or_404(org_repo, org_id)
    actor = await require_org_role(
        member_repo, org_id=org_id, user_id=user_id, min_role=OrgRole.ADMIN
    )
    if body.role == OrgRole.OWNER:
        raise ValidationError("Cannot assign owner via member invite; transfer ownership separately")
    if body.role == OrgRole.ADMIN and actor.role != OrgRole.OWNER:
        raise AuthorizationError("Only the organization owner can add admins")

    target_id = UUID(body.user_id)
    if await member_repo.is_member(org_id, target_id):
        raise ValidationError("User is already a member of this organization")

    saved = await member_repo.add(
        OrganizationMember(organization_id=org_id, user_id=target_id, role=body.role)
    )
    return success_response(
        _member_payload(saved),
        request_id=getattr(request.state, "request_id", ""),
    )


@organizations_router.patch("/{org_id}/members/{member_user_id}")
async def update_member_role(
    org_id: UUID,
    member_user_id: UUID,
    body: UpdateMemberRoleRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    org = await get_org_or_404(org_repo, org_id)
    actor = await require_org_role(
        member_repo, org_id=org_id, user_id=user_id, min_role=OrgRole.ADMIN
    )
    target = await member_repo.get_member(org_id, member_user_id)
    if target is None:
        raise NotFoundError("OrganizationMember", str(member_user_id))
    if target.role == OrgRole.OWNER or member_user_id == org.owner_id:
        raise AuthorizationError("Cannot change the organization owner's role")
    if body.role == OrgRole.OWNER:
        raise ValidationError("Cannot promote to owner via this endpoint")
    if body.role == OrgRole.ADMIN and actor.role != OrgRole.OWNER:
        raise AuthorizationError("Only the organization owner can promote admins")

    updated = await member_repo.update_role(org_id, member_user_id, body.role)
    return success_response(
        _member_payload(updated),
        request_id=getattr(request.state, "request_id", ""),
    )


@organizations_router.delete("/{org_id}/members/{member_user_id}", status_code=204)
async def remove_member(
    org_id: UUID,
    member_user_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    org_repo = SQLAlchemyOrganizationRepository(session)
    member_repo = SQLAlchemyOrganizationMemberRepository(session)
    org = await get_org_or_404(org_repo, org_id)
    await require_org_role(member_repo, org_id=org_id, user_id=user_id, min_role=OrgRole.ADMIN)
    if member_user_id == org.owner_id:
        raise AuthorizationError("Cannot remove the organization owner")
    await member_repo.remove(org_id, member_user_id)
