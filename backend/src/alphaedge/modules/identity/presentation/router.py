from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.config import settings
from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.identity.application.commands import (
    CreateApiKeyCommand,
    GetCurrentUserQuery,
    ListApiKeysQuery,
    LoginUserCommand,
    LogoutUserCommand,
    RefreshTokenCommand,
    RegisterUserCommand,
    RevokeApiKeyCommand,
)
from alphaedge.modules.identity.application.handlers import (
    CreateApiKeyHandler,
    GetCurrentUserHandler,
    ListApiKeysHandler,
    LoginUserHandler,
    LogoutUserHandler,
    RefreshTokenHandler,
    RegisterUserHandler,
    RevokeApiKeyHandler,
)
from alphaedge.modules.identity.application.oauth_service import (
    find_or_create_oauth_user,
    issue_token_pair,
)
from alphaedge.modules.identity.domain.entities import OAuthProvider, RateLimitTier
from alphaedge.modules.identity.infrastructure.models import (
    SQLAlchemyApiKeyRepository,
    SQLAlchemyOAuthAccountRepository,
    SQLAlchemyRefreshTokenRepository,
    SQLAlchemyRoleRepository,
    SQLAlchemyUserRepository,
)
from alphaedge.modules.identity.infrastructure.oauth import (
    build_authorization_url,
    exchange_code,
    store_oauth_state,
    verify_oauth_state,
)
from alphaedge.modules.identity.presentation.schemas import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    CreateApiKeyResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from alphaedge.shared.domain.exceptions import ValidationError
from alphaedge.shared.presentation.envelope import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_repos(session: AsyncSession):
    return (
        SQLAlchemyUserRepository(session),
        SQLAlchemyRoleRepository(session),
        SQLAlchemyRefreshTokenRepository(session),
        SQLAlchemyOAuthAccountRepository(session),
        SQLAlchemyApiKeyRepository(session),
    )


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, role_repo, _, _, _ = _get_repos(session)
    handler = RegisterUserHandler(user_repo, role_repo)
    result = await handler.handle(
        RegisterUserCommand(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
    )
    return success_response(
        UserResponse(
            id=str(result.id),
            email=result.email,
            display_name=result.display_name,
            roles=result.roles,
            is_active=result.is_active,
        ).model_dump(),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, _, token_repo, _, _ = _get_repos(session)
    handler = LoginUserHandler(user_repo, token_repo)
    result = await handler.handle(LoginUserCommand(email=body.email, password=body.password))
    return success_response(
        TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
        ).model_dump(),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, _, token_repo, _, _ = _get_repos(session)
    handler = RefreshTokenHandler(user_repo, token_repo)
    result = await handler.handle(RefreshTokenCommand(refresh_token=body.refresh_token))
    return success_response(
        TokenResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
        ).model_dump(),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
):
    _, _, token_repo, _, _ = _get_repos(session)
    handler = LogoutUserHandler(token_repo)
    await handler.handle(LogoutUserCommand(refresh_token=body.refresh_token))


@router.get("/me")
async def me(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, _, _, _, _ = _get_repos(session)
    handler = GetCurrentUserHandler(user_repo)
    result = await handler.handle(GetCurrentUserQuery(user_id=user_id))
    return success_response(
        UserResponse(
            id=str(result.id),
            email=result.email,
            display_name=result.display_name,
            roles=result.roles,
            is_active=result.is_active,
        ).model_dump(),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/oauth/{provider}")
async def oauth_start(provider: str):
    try:
        oauth_provider = OAuthProvider(provider)
    except ValueError as exc:
        raise ValidationError(f"Unsupported OAuth provider: {provider}") from exc
    url, state = build_authorization_url(oauth_provider)
    await store_oauth_state(state)
    return RedirectResponse(url)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    session: AsyncSession = Depends(get_db_session),
):
    if not await verify_oauth_state(state):
        raise ValidationError("Invalid or expired OAuth state")

    try:
        oauth_provider = OAuthProvider(provider)
    except ValueError as exc:
        raise ValidationError(f"Unsupported OAuth provider: {provider}") from exc

    user_repo, role_repo, token_repo, oauth_repo, _ = _get_repos(session)
    info = await exchange_code(oauth_provider, code)
    user = await find_or_create_oauth_user(user_repo, role_repo, oauth_repo, oauth_provider, info)
    access_token, refresh_token = await issue_token_pair(user, token_repo)

    redirect_url = (
        f"{settings.oauth_frontend_callback_url}"
        f"?access_token={access_token}&refresh_token={refresh_token}"
    )
    return RedirectResponse(redirect_url)


@router.post("/api-keys", status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    _, _, _, _, api_key_repo = _get_repos(session)
    try:
        tier = RateLimitTier(body.rate_limit_tier)
    except ValueError as exc:
        raise ValidationError(f"Invalid rate limit tier: {body.rate_limit_tier}") from exc
    handler = CreateApiKeyHandler(api_key_repo)
    result = await handler.handle(
        CreateApiKeyCommand(
            user_id=user_id,
            name=body.name,
            scopes=body.scopes,
            rate_limit_tier=tier,
        )
    )
    return success_response(
        CreateApiKeyResponse(
            api_key=ApiKeyResponse(
                id=str(result.api_key.id),
                name=result.api_key.name,
                prefix=result.api_key.prefix,
                scopes=result.api_key.scopes,
                rate_limit_tier=result.api_key.rate_limit_tier,
                created_at=result.api_key.created_at,
                last_used_at=result.api_key.last_used_at,
            ),
            key=result.raw_key,
        ).model_dump(),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.get("/api-keys")
async def list_api_keys(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    _, _, _, _, api_key_repo = _get_repos(session)
    handler = ListApiKeysHandler(api_key_repo)
    items = await handler.handle(ListApiKeysQuery(user_id=user_id))
    return success_response(
        {
            "items": [
                ApiKeyResponse(
                    id=str(k.id),
                    name=k.name,
                    prefix=k.prefix,
                    scopes=k.scopes,
                    rate_limit_tier=k.rate_limit_tier,
                    created_at=k.created_at,
                    last_used_at=k.last_used_at,
                ).model_dump()
                for k in items
            ]
        },
        request_id=getattr(request.state, "request_id", ""),
    )


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    _, _, _, _, api_key_repo = _get_repos(session)
    handler = RevokeApiKeyHandler(api_key_repo)
    await handler.handle(RevokeApiKeyCommand(user_id=user_id, key_id=key_id))
