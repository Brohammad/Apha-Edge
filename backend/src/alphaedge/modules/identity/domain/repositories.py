from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.identity.domain.entities import (
    ApiKey,
    OAuthAccount,
    RefreshToken,
    Role,
    User,
)


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...

    @abstractmethod
    async def get_by_verification_token_hash(self, token_hash: str) -> User | None: ...


class RoleRepository(ABC):
    @abstractmethod
    async def get_by_name(self, name: str) -> Role | None: ...

    @abstractmethod
    async def get_default_roles(self) -> list[Role]: ...

    @abstractmethod
    async def assign_role(self, user_id: UUID, role_id: UUID) -> None: ...


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def save(self, token: RefreshToken) -> RefreshToken: ...

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    @abstractmethod
    async def revoke(self, token_id: UUID) -> None: ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID) -> None: ...


class OAuthAccountRepository(ABC):
    @abstractmethod
    async def get_by_provider_uid(
        self, provider: str, provider_uid: str
    ) -> OAuthAccount | None: ...

    @abstractmethod
    async def save(self, account: OAuthAccount) -> OAuthAccount: ...


class ApiKeyRepository(ABC):
    @abstractmethod
    async def save(self, api_key: ApiKey) -> ApiKey: ...

    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> ApiKey | None: ...

    @abstractmethod
    async def list_by_user_id(self, user_id: UUID) -> list[ApiKey]: ...

    @abstractmethod
    async def revoke(self, key_id: UUID) -> None: ...

    @abstractmethod
    async def touch_last_used(self, key_id: UUID) -> None: ...
