from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from alphaedge.modules.organization.domain.enums import OrgRole
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass
class Organization:
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    plan_tier: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(
        name: str, slug: str, owner_id: UUID, *, plan_tier: str = "standard"
    ) -> "Organization":
        name = name.strip()
        slug = slug.strip().lower()
        if not name:
            raise ValidationError("Organization name is required")
        if not slug or " " in slug:
            raise ValidationError("Organization slug must be a single token")
        return Organization(
            id=uuid4(),
            name=name,
            slug=slug,
            owner_id=owner_id,
            plan_tier=plan_tier,
        )


@dataclass
class OrganizationMember:
    organization_id: UUID
    user_id: UUID
    role: OrgRole
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
