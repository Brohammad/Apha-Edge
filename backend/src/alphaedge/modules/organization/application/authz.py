"""Organization membership authorization helpers."""

from __future__ import annotations

from uuid import UUID

from alphaedge.modules.organization.domain.entities import OrganizationMember
from alphaedge.modules.organization.domain.enums import OrgRole
from alphaedge.modules.organization.domain.repositories import OrganizationMemberRepository
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError

_ROLE_RANK = {
    OrgRole.MEMBER: 1,
    OrgRole.ADMIN: 2,
    OrgRole.OWNER: 3,
}


def role_at_least(actual: OrgRole, minimum: OrgRole) -> bool:
    return _ROLE_RANK[actual] >= _ROLE_RANK[minimum]


async def require_org_role(
    member_repo: OrganizationMemberRepository,
    *,
    org_id: UUID,
    user_id: UUID,
    min_role: OrgRole = OrgRole.MEMBER,
) -> OrganizationMember:
    member = await member_repo.get_member(org_id, user_id)
    if member is None:
        raise AuthorizationError("You are not a member of this organization")
    if not role_at_least(member.role, min_role):
        raise AuthorizationError(
            f"Organization role '{min_role.value}' or higher is required"
        )
    return member


async def get_org_or_404(org_repo, org_id: UUID):
    org = await org_repo.get_by_id(org_id)
    if org is None:
        raise NotFoundError("Organization", str(org_id))
    return org
