from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from alphaedge.shared.domain.exceptions import ValidationError


class RoleName(StrEnum):
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"
    API_SERVICE = "api_service"


class OAuthProvider(StrEnum):
    GOOGLE = "google"
    GITHUB = "github"


class RateLimitTier(StrEnum):
    FREE = "free"
    STANDARD = "standard"
    PRO = "pro"
    UNLIMITED = "unlimited"


@dataclass
class Role:
    id: UUID
    name: RoleName
    description: str = ""


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str | None
    display_name: str
    is_active: bool = True
    rate_limit_tier: RateLimitTier = RateLimitTier.STANDARD
    roles: list[Role] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def create(email: str, password_hash: str | None, display_name: str) -> "User":
        if not email or "@" not in email:
            raise ValidationError("Invalid email address")
        if not display_name.strip():
            raise ValidationError("Display name is required")
        return User(
            id=uuid4(),
            email=email.lower().strip(),
            password_hash=password_hash,
            display_name=display_name.strip(),
        )

    def has_role(self, role_name: RoleName) -> bool:
        return any(r.name == role_name for r in self.roles)

    def has_permission(self, permission: str) -> bool:
        role_permissions = {
            RoleName.ADMIN: {"*"},
            RoleName.TRADER: {
                "read:strategies",
                "write:strategies",
                "read:backtests",
                "write:backtests",
                "read:portfolios",
                "write:portfolios",
                "read:orders",
                "write:orders",
            },
            RoleName.VIEWER: {
                "read:strategies",
                "read:backtests",
                "read:portfolios",
                "read:orders",
            },
            RoleName.API_SERVICE: {"read:*", "write:*"},
        }
        for role in self.roles:
            perms = role_permissions.get(role.name, set())
            if "*" in perms or permission in perms:
                return True
            category = permission.split(":")[0]
            if f"{category}:*" in perms or "read:*" in perms or "write:*" in perms:
                return True
        return False


@dataclass
class RefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        return datetime.now(UTC) < self.expires_at


@dataclass
class OAuthAccount:
    id: UUID
    user_id: UUID
    provider: OAuthProvider
    provider_uid: str
    email: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ApiKey:
    id: UUID
    user_id: UUID
    name: str
    key_hash: str
    prefix: str
    scopes: list[str]
    rate_limit_tier: RateLimitTier
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        return not (self.expires_at is not None and datetime.now(UTC) >= self.expires_at)
