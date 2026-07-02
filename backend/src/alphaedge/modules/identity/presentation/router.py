from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.dependencies import get_current_user_id, get_db_session
from alphaedge.modules.identity.application.commands import (
    GetCurrentUserQuery,
    LoginUserCommand,
    LogoutUserCommand,
    RefreshTokenCommand,
    RegisterUserCommand,
)
from alphaedge.modules.identity.application.handlers import (
    GetCurrentUserHandler,
    LoginUserHandler,
    LogoutUserHandler,
    RefreshTokenHandler,
    RegisterUserHandler,
)
from alphaedge.modules.identity.infrastructure.models import (
    SQLAlchemyRefreshTokenRepository,
    SQLAlchemyRoleRepository,
    SQLAlchemyUserRepository,
)
from alphaedge.modules.identity.presentation.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from alphaedge.shared.presentation.envelope import success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_repos(session: AsyncSession):
    return (
        SQLAlchemyUserRepository(session),
        SQLAlchemyRoleRepository(session),
        SQLAlchemyRefreshTokenRepository(session),
    )


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, role_repo, _ = _get_repos(session)
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
    user_repo, _, token_repo = _get_repos(session)
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
    user_repo, _, token_repo = _get_repos(session)
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
    _, _, token_repo = _get_repos(session)
    handler = LogoutUserHandler(token_repo)
    await handler.handle(LogoutUserCommand(refresh_token=body.refresh_token))


@router.get("/me")
async def me(
    request: Request,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    user_repo, _, _ = _get_repos(session)
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
