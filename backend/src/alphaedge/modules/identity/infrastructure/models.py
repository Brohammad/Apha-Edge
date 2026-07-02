from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alphaedge.modules.identity.domain.entities import RefreshToken, Role, RoleName, User
from alphaedge.modules.identity.domain.repositories import (
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from alphaedge.shared.infrastructure.database import Base, TimestampMixin, UUIDPrimaryKeyMixin

user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("role_id", PGUUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), nullable=False),
)


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    roles: Mapped[list["RoleModel"]] = relationship(secondary=user_roles_table, lazy="selectin")


class RoleModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")


class RefreshTokenModel(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)


def _role_to_entity(model: RoleModel) -> Role:
    return Role(id=model.id, name=RoleName(model.name), description=model.description)


def _user_to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        display_name=model.display_name,
        is_active=model.is_active,
        roles=[_role_to_entity(r) for r in model.roles],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _user_to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.lower().strip())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _user_to_entity(model) if model else None

    async def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            display_name=user.display_name,
            is_active=user.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        return user


class SQLAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(RoleModel).where(RoleModel.name == name)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _role_to_entity(model) if model else None

    async def get_default_roles(self) -> list[Role]:
        stmt = select(RoleModel).where(RoleModel.name == RoleName.TRADER.value)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return [_role_to_entity(model)] if model else []

    async def assign_role(self, user_id: UUID, role_id: UUID) -> None:
        from datetime import UTC, datetime

        await self._session.execute(
            user_roles_table.insert().values(
                user_id=user_id,
                role_id=role_id,
                assigned_at=datetime.now(UTC),
            )
        )


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
        )
        self._session.add(model)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )

    async def revoke(self, token_id: UUID) -> None:
        from datetime import UTC, datetime

        stmt = select(RefreshTokenModel).where(RefreshTokenModel.id == token_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        model.revoked_at = datetime.now(UTC)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        from datetime import UTC, datetime

        stmt = select(RefreshTokenModel).where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        for model in result.scalars():
            model.revoked_at = datetime.now(UTC)
