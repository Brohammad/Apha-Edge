from datetime import UTC, datetime, timedelta
from uuid import uuid4

from alphaedge.config import settings
from alphaedge.modules.identity.application.commands import (
    GetCurrentUserQuery,
    LoginUserCommand,
    LogoutUserCommand,
    RefreshTokenCommand,
    RegisterUserCommand,
    TokenPair,
    UserDTO,
)
from alphaedge.modules.identity.application.services import PasswordService, TokenService
from alphaedge.modules.identity.domain.entities import RefreshToken, User
from alphaedge.modules.identity.domain.repositories import (
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from alphaedge.shared.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
)


class RegisterUserHandler:
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository) -> None:
        self._user_repo = user_repo
        self._role_repo = role_repo

    async def handle(self, command: RegisterUserCommand) -> UserDTO:
        existing = await self._user_repo.get_by_email(command.email)
        if existing:
            raise ConflictError(f"User with email {command.email} already exists")

        password_hash = PasswordService.hash(command.password)
        user = User.create(command.email, password_hash, command.display_name)

        default_roles = await self._role_repo.get_default_roles()
        user.roles = default_roles

        saved = await self._user_repo.save(user)
        for role in default_roles:
            await self._role_repo.assign_role(saved.id, role.id)

        return UserDTO.from_entity(saved)


class LoginUserHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo

    async def handle(self, command: LoginUserCommand) -> TokenPair:
        user = await self._user_repo.get_by_email(command.email)
        if not user or not PasswordService.verify(command.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        roles = [r.name.value for r in user.roles]
        access_token = TokenService.create_access_token(str(user.id), roles)

        raw_refresh, refresh_entity = TokenService.build_refresh_token(user.id)
        await self._token_repo.save(refresh_entity)

        return TokenPair(access_token=access_token, refresh_token=raw_refresh)


class RefreshTokenHandler:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo

    async def handle(self, command: RefreshTokenCommand) -> TokenPair:
        token_hash = TokenService.hash_token(command.refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)

        if not stored or not stored.is_valid:
            raise AuthenticationError("Invalid or expired refresh token")

        user = await self._user_repo.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        await self._token_repo.revoke(stored.id)

        roles = [r.name.value for r in user.roles]
        access_token = TokenService.create_access_token(str(user.id), roles)

        raw_refresh = TokenService.create_refresh_token_value()
        new_refresh = RefreshToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=TokenService.hash_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days),
        )
        await self._token_repo.save(new_refresh)

        return TokenPair(access_token=access_token, refresh_token=raw_refresh)


class LogoutUserHandler:
    def __init__(self, token_repo: RefreshTokenRepository) -> None:
        self._token_repo = token_repo

    async def handle(self, command: LogoutUserCommand) -> None:
        token_hash = TokenService.hash_token(command.refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)
        if stored:
            await self._token_repo.revoke(stored.id)


class GetCurrentUserHandler:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def handle(self, query: GetCurrentUserQuery) -> UserDTO:
        user = await self._user_repo.get_by_id(query.user_id)
        if not user:
            raise NotFoundError("User", str(query.user_id))
        return UserDTO.from_entity(user)
