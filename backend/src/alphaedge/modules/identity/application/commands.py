from dataclasses import dataclass
from uuid import UUID

from alphaedge.modules.identity.domain.entities import RateLimitTier, User


@dataclass(frozen=True)
class RegisterUserCommand:
    email: str
    password: str
    display_name: str


@dataclass(frozen=True)
class LoginUserCommand:
    email: str
    password: str


@dataclass(frozen=True)
class RefreshTokenCommand:
    refresh_token: str


@dataclass(frozen=True)
class LogoutUserCommand:
    refresh_token: str


@dataclass(frozen=True)
class GetCurrentUserQuery:
    user_id: UUID


@dataclass(frozen=True)
class CreateApiKeyCommand:
    user_id: UUID
    name: str
    scopes: list[str]
    rate_limit_tier: RateLimitTier = RateLimitTier.STANDARD


@dataclass(frozen=True)
class ListApiKeysQuery:
    user_id: UUID


@dataclass(frozen=True)
class RevokeApiKeyCommand:
    user_id: UUID
    key_id: UUID


@dataclass(frozen=True)
class ApiKeyDTO:
    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    rate_limit_tier: str
    created_at: object
    last_used_at: object | None

    @staticmethod
    def from_entity(entity: object) -> "ApiKeyDTO":
        return ApiKeyDTO(
            id=entity.id,
            name=entity.name,
            prefix=entity.prefix,
            scopes=entity.scopes,
            rate_limit_tier=entity.rate_limit_tier.value,
            created_at=entity.created_at,
            last_used_at=entity.last_used_at,
        )


@dataclass(frozen=True)
class CreateApiKeyResult:
    api_key: ApiKeyDTO
    raw_key: str


@dataclass(frozen=True)
class VerifyEmailCommand:
    token: str


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True)
class UserDTO:
    id: UUID
    email: str
    display_name: str
    roles: list[str]
    is_active: bool
    email_verified: bool

    @staticmethod
    def from_entity(user: User) -> "UserDTO":
        return UserDTO(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            roles=[r.name.value for r in user.roles],
            is_active=user.is_active,
            email_verified=user.email_verified,
        )
