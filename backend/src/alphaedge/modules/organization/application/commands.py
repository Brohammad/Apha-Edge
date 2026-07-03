from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateOrganizationCommand:
    user_id: UUID
    name: str
    slug: str


@dataclass(frozen=True)
class ListOrganizationsQuery:
    user_id: UUID


@dataclass(frozen=True)
class OrganizationDTO:
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    plan_tier: str
    created_at: datetime

    @staticmethod
    def from_entity(entity: object) -> "OrganizationDTO":
        return OrganizationDTO(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            owner_id=entity.owner_id,
            plan_tier=entity.plan_tier,
            created_at=entity.created_at,
        )
