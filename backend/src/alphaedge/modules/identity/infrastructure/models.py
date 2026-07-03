from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alphaedge.modules.identity.domain.entities import (
    ApiKey,
    OAuthAccount,
    OAuthProvider,
    RateLimitTier,
    RefreshToken,
    Role,
    RoleName,
    User,
)
from alphaedge.modules.identity.domain.repositories import (
    ApiKeyRepository,
    OAuthAccountRepository,
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
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    rate_limit_tier: Mapped[str] = mapped_column(String(20), default=RateLimitTier.STANDARD.value)

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
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OAuthAccountModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "oauth_accounts"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ApiKeyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "api_keys"

    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(12), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    rate_limit_tier: Mapped[str] = mapped_column(String(20), default=RateLimitTier.STANDARD.value)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _role_to_entity(model: RoleModel) -> Role:
    return Role(id=model.id, name=RoleName(model.name), description=model.description)


def _user_to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        display_name=model.display_name,
        is_active=model.is_active,
        rate_limit_tier=RateLimitTier(model.rate_limit_tier),
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


def _oauth_to_entity(model: OAuthAccountModel) -> OAuthAccount:
    return OAuthAccount(
        id=model.id,
        user_id=model.user_id,
        provider=OAuthProvider(model.provider),
        provider_uid=model.provider_uid,
        email=model.email,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _api_key_to_entity(model: ApiKeyModel) -> ApiKey:
    return ApiKey(
        id=model.id,
        user_id=model.user_id,
        name=model.name,
        key_hash=model.key_hash,
        prefix=model.prefix,
        scopes=list(model.scopes or []),
        rate_limit_tier=RateLimitTier(model.rate_limit_tier),
        expires_at=model.expires_at,
        last_used_at=model.last_used_at,
        revoked_at=model.revoked_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyOAuthAccountRepository(OAuthAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_provider_uid(self, provider: str, provider_uid: str) -> OAuthAccount | None:
        stmt = select(OAuthAccountModel).where(
            OAuthAccountModel.provider == provider,
            OAuthAccountModel.provider_uid == provider_uid,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _oauth_to_entity(model) if model else None

    async def save(self, account: OAuthAccount) -> OAuthAccount:
        model = OAuthAccountModel(
            id=account.id,
            user_id=account.user_id,
            provider=account.provider.value,
            provider_uid=account.provider_uid,
            email=account.email,
        )
        self._session.add(model)
        await self._session.flush()
        return account


class SQLAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, api_key: ApiKey) -> ApiKey:
        model = ApiKeyModel(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            key_hash=api_key.key_hash,
            prefix=api_key.prefix,
            scopes=api_key.scopes,
            rate_limit_tier=api_key.rate_limit_tier.value,
            expires_at=api_key.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return api_key

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _api_key_to_entity(model) if model else None

    async def list_by_user_id(self, user_id: UUID) -> list[ApiKey]:
        stmt = (
            select(ApiKeyModel)
            .where(ApiKeyModel.user_id == user_id, ApiKeyModel.revoked_at.is_(None))
            .order_by(ApiKeyModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_api_key_to_entity(m) for m in result.scalars()]

    async def revoke(self, key_id: UUID) -> None:
        from datetime import UTC, datetime

        model = await self._session.get(ApiKeyModel, key_id)
        if model:
            model.revoked_at = datetime.now(UTC)

    async def touch_last_used(self, key_id: UUID) -> None:
        from datetime import UTC, datetime

        model = await self._session.get(ApiKeyModel, key_id)
        if model:
            model.last_used_at = datetime.now(UTC)
