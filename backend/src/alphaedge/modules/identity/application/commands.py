from dataclasses import dataclass
from uuid import UUID

from alphaedge.modules.identity.domain.entities import User


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

    @staticmethod
    def from_entity(user: User) -> "UserDTO":
        return UserDTO(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            roles=[r.name.value for r in user.roles],
            is_active=user.is_active,
        )
