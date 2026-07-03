from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.modules.identity.application.oauth_service import resolve_api_key
from alphaedge.modules.identity.application.services import TokenService
from alphaedge.modules.identity.infrastructure.models import SQLAlchemyApiKeyRepository
from alphaedge.shared.domain.exceptions import AuthenticationError
from alphaedge.shared.infrastructure.database import async_session_factory

security = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> UUID:
    if x_api_key:
        async with async_session_factory() as session:
            api_key_repo = SQLAlchemyApiKeyRepository(session)
            user_id, _ = await resolve_api_key(api_key_repo, x_api_key)
            await session.commit()
            return user_id

    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    payload = TokenService.decode_access_token(credentials.credentials)
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise AuthenticationError("Invalid token payload")

    return UUID(sub)


async def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UUID | None:
    if credentials is None:
        return None
    try:
        return await get_current_user_id(credentials)
    except AuthenticationError:
        return None
