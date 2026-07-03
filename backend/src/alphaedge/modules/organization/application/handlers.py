from alphaedge.modules.organization.application.commands import (
    CreateOrganizationCommand,
    ListOrganizationsQuery,
    OrganizationDTO,
)
from alphaedge.modules.organization.domain.entities import Organization, OrganizationMember
from alphaedge.modules.organization.domain.enums import OrgRole
from alphaedge.modules.organization.domain.repositories import (
    OrganizationMemberRepository,
    OrganizationRepository,
)
from alphaedge.shared.domain.exceptions import ConflictError


class CreateOrganizationHandler:
    def __init__(
        self,
        org_repo: OrganizationRepository,
        member_repo: OrganizationMemberRepository,
    ) -> None:
        self._org_repo = org_repo
        self._member_repo = member_repo

    async def handle(self, command: CreateOrganizationCommand) -> OrganizationDTO:
        existing = await self._org_repo.get_by_slug(command.slug)
        if existing:
            raise ConflictError(f"Organization slug '{command.slug}' is taken")
        org = Organization.create(command.name, command.slug, command.user_id)
        saved = await self._org_repo.save(org)
        await self._member_repo.add(OrganizationMember(saved.id, command.user_id, OrgRole.OWNER))
        return OrganizationDTO.from_entity(saved)


class ListOrganizationsHandler:
    def __init__(self, org_repo: OrganizationRepository) -> None:
        self._org_repo = org_repo

    async def handle(self, query: ListOrganizationsQuery) -> list[OrganizationDTO]:
        orgs = await self._org_repo.list_for_user(query.user_id)
        return [OrganizationDTO.from_entity(o) for o in orgs]
