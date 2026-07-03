from uuid import UUID

from fastapi import Request

from alphaedge.modules.identity.application.services import TokenService
from alphaedge.modules.identity.infrastructure.models import (
    SQLAlchemyApiKeyRepository,
    SQLAlchemyUserRepository,
)
from alphaedge.shared.domain.exceptions import AuthenticationError
from alphaedge.shared.infrastructure.database import async_session_factory


async def auth_context_middleware(request: Request, call_next):
    """Resolve JWT or API key and attach user/tier to request.state for rate limiting."""
    request.state.user_id = None
    request.state.rate_limit_tier = "anonymous"
    request.state.api_key_id = None

    api_key = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization", "")

    async with async_session_factory() as session:
        if api_key:
            from alphaedge.modules.identity.application.oauth_service import (
                resolve_api_key,
            )

            try:
                api_key_repo = SQLAlchemyApiKeyRepository(session)
                user_id, key_entity = await resolve_api_key(api_key_repo, api_key)
                user_repo = SQLAlchemyUserRepository(session)
                user = await user_repo.get_by_id(user_id)
                if not user or not user.is_active:
                    raise AuthenticationError("Account is deactivated")
                request.state.user_id = user_id
                request.state.api_key_id = key_entity.id
                request.state.rate_limit_tier = key_entity.rate_limit_tier.value
                await session.commit()
            except AuthenticationError:
                await session.rollback()
        elif auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = TokenService.decode_access_token(token)
                sub = payload.get("sub")
                if sub and isinstance(sub, str):
                    user_id = UUID(sub)
                    user_repo = SQLAlchemyUserRepository(session)
                    user = await user_repo.get_by_id(user_id)
                    if not user or not user.is_active:
                        raise AuthenticationError("Account is deactivated")
                    request.state.user_id = user_id
                    tier = user.rate_limit_tier.value
                    if any(r.name.value == "admin" for r in user.roles):
                        tier = "unlimited"
                    request.state.rate_limit_tier = tier
            except (AuthenticationError, ValueError):
                pass

    return await call_next(request)
