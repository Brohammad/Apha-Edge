from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.organization.domain.entities import Organization, OrganizationMember


class OrganizationRepository(ABC):
    @abstractmethod
    async def save(self, org: Organization) -> Organization: ...

    @abstractmethod
    async def get_by_id(self, org_id: UUID) -> Organization | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Organization | None: ...

    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[Organization]: ...


class OrganizationMemberRepository(ABC):
    @abstractmethod
    async def add(self, member: OrganizationMember) -> OrganizationMember: ...

    @abstractmethod
    async def list_members(self, org_id: UUID) -> list[OrganizationMember]: ...

    @abstractmethod
    async def is_member(self, org_id: UUID, user_id: UUID) -> bool: ...
