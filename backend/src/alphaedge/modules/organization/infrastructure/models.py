from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from alphaedge.modules.organization.domain.entities import Organization, OrganizationMember
from alphaedge.modules.organization.domain.enums import OrgRole
from alphaedge.modules.organization.domain.repositories import (
    OrganizationMemberRepository,
    OrganizationRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    plan_tier: Mapped[str] = mapped_column(default="standard")


class OrganizationMemberModel(Base):
    __tablename__ = "organization_members"

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, nullable=False)
    role: Mapped[str] = mapped_column(default=OrgRole.MEMBER.value)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _org_entity(m: OrganizationModel) -> Organization:
    return Organization(
        id=m.id,
        name=m.name,
        slug=m.slug,
        owner_id=m.owner_id,
        plan_tier=m.plan_tier,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


class SQLAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, org: Organization) -> Organization:
        model = OrganizationModel(
            id=org.id,
            name=org.name,
            slug=org.slug,
            owner_id=org.owner_id,
            plan_tier=org.plan_tier,
        )
        self._session.add(model)
        await self._session.flush()
        return org

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        model = await self._session.get(OrganizationModel, org_id)
        return _org_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(OrganizationModel).where(OrganizationModel.slug == slug.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _org_entity(model) if model else None

    async def list_for_user(self, user_id: UUID) -> list[Organization]:
        stmt = (
            select(OrganizationModel)
            .join(
                OrganizationMemberModel,
                OrganizationMemberModel.organization_id == OrganizationModel.id,
            )
            .where(OrganizationMemberModel.user_id == user_id)
            .order_by(OrganizationModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_org_entity(m) for m in result.scalars().all()]


class SQLAlchemyOrganizationMemberRepository(OrganizationMemberRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, member: OrganizationMember) -> OrganizationMember:
        model = OrganizationMemberModel(
            organization_id=member.organization_id,
            user_id=member.user_id,
            role=member.role.value,
            joined_at=member.joined_at,
        )
        self._session.add(model)
        await self._session.flush()
        return member

    async def list_members(self, org_id: UUID) -> list[OrganizationMember]:
        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.organization_id == org_id
        )
        result = await self._session.execute(stmt)
        return [
            OrganizationMember(
                organization_id=m.organization_id,
                user_id=m.user_id,
                role=OrgRole(m.role),
                joined_at=m.joined_at,
            )
            for m in result.scalars().all()
        ]

    async def is_member(self, org_id: UUID, user_id: UUID) -> bool:
        stmt = select(OrganizationMemberModel).where(
            OrganizationMemberModel.organization_id == org_id,
            OrganizationMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
