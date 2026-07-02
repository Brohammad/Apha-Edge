from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.modules.identity.application.services import TokenService
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
) -> UUID:
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
