from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.config import settings
from alphaedge.dependencies import get_auth_context, get_current_user_id, get_db_session
from alphaedge.modules.identity.application.commands import (
    CreateApiKeyCommand,
    GetCurrentUserQuery,
    ListApiKeysQuery,
    LoginUserCommand,
    LogoutUserCommand,
    RefreshTokenCommand,
    RegisterUserCommand,
    RevokeApiKeyCommand,
    VerifyEmailCommand,
)
from alphaedge.modules.identity.application.handlers import (
    CreateApiKeyHandler,
    GetCurrentUserHandler,
    ListApiKeysHandler,
    LoginUserHandler,
    LogoutUserHandler,
    RefreshTokenHandler,
    RegisterUserHandler,
    ResendVerificationHandler,
    RevokeApiKeyHandler,
    VerifyEmailHandler,
)
from alphaedge.modules.identity.application.oauth_service import (
    find_or_create_oauth_user,
    issue_token_pair,
)
from alphaedge.modules.identity.domain.entities import OAuthProvider, RateLimitTier, RoleName
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
    VerifyEmailRequest,
)
from alphaedge.shared.domain.exceptions import AuthorizationError, ValidationError
from alphaedge.shared.infrastructure.audit import record_audit
from alphaedge.shared.infrastructure.ws_tickets import issue_ws_ticket
from alphaedge.shared.presentation.cookies import (
    clear_auth_cookies,
    read_access_token,
    read_refresh_token,
    set_access_cookie,
    set_refresh_cookie,
)
from alphaedge.shared.presentation.envelope import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_response(result: object) -> dict:
    return UserResponse(
        id=str(result.id),
        email=result.email,
        display_name=result.display_name,
        roles=result.roles,
        is_active=result.is_active,
        email_verified=result.email_verified,
    ).model_dump()


def _token_json_response(
    request: Request,
    access_token: str,
    refresh_token: str,
    *,
    include_tokens_in_body: bool = False,
) -> JSONResponse:
    data = TokenResponse(
        access_token=access_token if include_tokens_in_body else "",
        refresh_token=refresh_token if include_tokens_in_body else None,
    ).model_dump()
    envelope = success_response(data, request_id=getattr(request.state, "request_id", ""))
    response = JSONResponse(content=envelope)
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)
    return response


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
        _user_response(result),
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
    await record_audit(
        session,
        user_id=None,
        action="auth.login",
        resource_type="user",
        request=request,
        changes={"email": body.email},
    )
    mobile_client = request.headers.get("X-Client-Type") == "mobile"
    return _token_json_response(
        request,
        result.access_token,
        result.refresh_token,
        include_tokens_in_body=mobile_client,
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    refresh_token = read_refresh_token(request, body.refresh_token)
    if not refresh_token:
        raise ValidationError("Refresh token required")
    user_repo, _, token_repo, _, _ = _get_repos(session)
    handler = RefreshTokenHandler(user_repo, token_repo)
    result = await handler.handle(RefreshTokenCommand(refresh_token=refresh_token))
    mobile_client = request.headers.get("X-Client-Type") == "mobile"
    return _token_json_response(
        request,
        result.access_token,
        result.refresh_token,
        include_tokens_in_body=mobile_client,
    )


@router.post("/logout", status_code=204)
async def logout(
    body: LogoutRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    refresh_token = read_refresh_token(request, body.refresh_token)
    _, _, token_repo, _, _ = _get_repos(session)
    handler = LogoutUserHandler(token_repo)
    await handler.handle(LogoutUserCommand(refresh_token=refresh_token or ""))
    response = JSONResponse(status_code=204, content=None)
    clear_auth_cookies(response)
    return response


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, _, _, _, _ = _get_repos(session)
    handler = VerifyEmailHandler(user_repo)
    result = await handler.handle(VerifyEmailCommand(token=body.token))
    return success_response(
        _user_response(result),
        request_id=getattr(request.state, "request_id", ""),
    )


@router.post("/resend-verification")
async def resend_verification(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, _, _, _, _ = _get_repos(session)
    handler = ResendVerificationHandler(user_repo)
    dev_token = await handler.handle(user_id)
    payload: dict[str, object] = {"sent": dev_token is None}
    if dev_token:
        payload["verification_token"] = dev_token
    return success_response(payload, request_id=getattr(request.state, "request_id", ""))


@router.post("/ws-ticket")
async def create_ws_ticket(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
):
    ticket = await issue_ws_ticket(user_id)
    return success_response({"ticket": ticket}, request_id=getattr(request.state, "request_id", ""))


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
        _user_response(result),
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
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    if error:
        return RedirectResponse(f"{settings.oauth_frontend_callback_url}?error={quote(error)}")
    if not code or not state:
        return RedirectResponse(
            f"{settings.oauth_frontend_callback_url}?error={quote('missing_oauth_code')}"
        )

    if not await verify_oauth_state(state):
        return RedirectResponse(
            f"{settings.oauth_frontend_callback_url}?error={quote('invalid_oauth_state')}"
        )

    try:
        oauth_provider = OAuthProvider(provider)
    except ValueError as exc:
        raise ValidationError(f"Unsupported OAuth provider: {provider}") from exc

    try:
        user_repo, role_repo, token_repo, oauth_repo, _ = _get_repos(session)
        info = await exchange_code(oauth_provider, code)
        user = await find_or_create_oauth_user(
            user_repo, role_repo, oauth_repo, oauth_provider, info
        )
        access_token, refresh_token = await issue_token_pair(user, token_repo)
    except Exception:
        return RedirectResponse(
            f"{settings.oauth_frontend_callback_url}?error={quote('oauth_exchange_failed')}"
        )

    redirect_url = f"{settings.oauth_frontend_callback_url}?oauth=success"
    response = RedirectResponse(redirect_url)
    set_access_cookie(response, access_token)
    set_refresh_cookie(response, refresh_token)
    return response


@router.post("/api-keys", status_code=201)
async def create_api_key(
    body: CreateApiKeyRequest,
    request: Request,
    auth=Depends(get_auth_context),
    session: AsyncSession = Depends(get_db_session),
):
    user_id = auth.user_id
    _, _, _, _, api_key_repo = _get_repos(session)
    try:
        tier = RateLimitTier(body.rate_limit_tier)
    except ValueError as exc:
        raise ValidationError(f"Invalid rate limit tier: {body.rate_limit_tier}") from exc

    if auth.user and not auth.user.has_role(RoleName.ADMIN):
        user_tier = auth.user.rate_limit_tier
        tier_order = list(RateLimitTier)
        if tier_order.index(tier) > tier_order.index(user_tier):
            raise AuthorizationError("Cannot create API keys above your account rate limit tier")
        if tier == RateLimitTier.UNLIMITED:
            raise AuthorizationError("Unlimited API key tier requires admin role")

    handler = CreateApiKeyHandler(api_key_repo)
    result = await handler.handle(
        CreateApiKeyCommand(
            user_id=user_id,
            name=body.name,
            scopes=body.scopes,
            rate_limit_tier=tier,
        )
    )
    await record_audit(
        session,
        user_id=user_id,
        action="api_key.create",
        resource_type="api_key",
        resource_id=result.api_key.id,
        request=request,
        changes={"name": body.name, "scopes": body.scopes},
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
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    _, _, _, _, api_key_repo = _get_repos(session)
    handler = RevokeApiKeyHandler(api_key_repo)
    await handler.handle(RevokeApiKeyCommand(user_id=user_id, key_id=key_id))
    await record_audit(
        session,
        user_id=user_id,
        action="api_key.revoke",
        resource_type="api_key",
        resource_id=key_id,
        request=request,
    )
