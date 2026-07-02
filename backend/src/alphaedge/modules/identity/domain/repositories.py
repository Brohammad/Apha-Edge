from abc import ABC, abstractmethod
from uuid import UUID

from alphaedge.modules.identity.domain.entities import RefreshToken, Role, User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...


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
