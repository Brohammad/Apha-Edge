from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.modules.identity.application.oauth_service import resolve_api_key
from alphaedge.modules.identity.application.services import TokenService
from alphaedge.modules.identity.domain.entities import ApiKey, RoleName, User
from alphaedge.modules.identity.infrastructure.models import (
    SQLAlchemyApiKeyRepository,
    SQLAlchemyUserRepository,
)
from alphaedge.shared.domain.exceptions import AuthenticationError, AuthorizationError
from alphaedge.shared.infrastructure.database import async_session_factory
from alphaedge.shared.security.scopes import api_key_has_scope, required_scope_for_method

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    user: User | None = None
    api_key: ApiKey | None = None

    @property
    def is_api_key(self) -> bool:
        return self.api_key is not None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _resolve_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    x_api_key: str | None,
) -> AuthContext:
    if x_api_key:
        async with async_session_factory() as session:
            api_key_repo = SQLAlchemyApiKeyRepository(session)
            user_id, key_entity = await resolve_api_key(api_key_repo, x_api_key)
            required = required_scope_for_method(request.method)
            if not api_key_has_scope(key_entity.scopes, required):
                raise AuthorizationError(f"API key lacks required scope: {required}")
            user_repo = SQLAlchemyUserRepository(session)
            user = await user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise AuthenticationError("Account is deactivated")
            await session.commit()
            return AuthContext(user_id=user_id, user=user, api_key=key_entity)

    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    payload = TokenService.decode_access_token(credentials.credentials)
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise AuthenticationError("Invalid token payload")

    user_id = UUID(sub)
    async with async_session_factory() as session:
        user_repo = SQLAlchemyUserRepository(session)
        user = await user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")
        await session.commit()
        return AuthContext(user_id=user_id, user=user)


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    return await _resolve_auth(request, credentials, x_api_key)


async def get_current_user_id(
    auth: AuthContext = Depends(get_auth_context),
) -> UUID:
    return auth.user_id


def require_permission(permission: str) -> Callable[..., AuthContext]:
    async def _check(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth.is_api_key:
            if not api_key_has_scope(auth.api_key.scopes, permission):  # type: ignore[union-attr]
                raise AuthorizationError(f"API key lacks permission: {permission}")
            return auth
        if auth.user is None or not auth.user.has_permission(permission):
            raise AuthorizationError("Insufficient permissions")
        return auth

    return _check


async def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    from alphaedge.config import settings

    if settings.is_testing:
        return auth
    if auth.user is None or not auth.user.has_role(RoleName.ADMIN):
        raise AuthorizationError("Admin role required")
    return auth


async def require_verified_email(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    from alphaedge.config import settings

    if settings.is_testing or settings.is_development:
        return auth
    if auth.user is None or not auth.user.email_verified:
        raise AuthorizationError("Email verification required")
    return auth


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UUID | None:
    if credentials is None:
        return None
    try:
        payload = TokenService.decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        if sub and isinstance(sub, str):
            return UUID(sub)
    except AuthenticationError:
        return None
    return None
