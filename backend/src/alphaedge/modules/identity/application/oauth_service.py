import secrets
from uuid import UUID, uuid4

from alphaedge.modules.identity.application.services import TokenService
from alphaedge.modules.identity.domain.entities import (
    ApiKey,
    OAuthAccount,
    OAuthProvider,
    RateLimitTier,
    User,
)
from alphaedge.modules.identity.domain.repositories import (
    ApiKeyRepository,
    OAuthAccountRepository,
    RefreshTokenRepository,
    RoleRepository,
    UserRepository,
)
from alphaedge.modules.identity.infrastructure.oauth import OAuthUserInfo
from alphaedge.shared.domain.exceptions import AuthenticationError


class ApiKeyService:
    PREFIX = "ae_live_"

    @staticmethod
    def generate(
        name: str, user_id: UUID, scopes: list[str], tier: RateLimitTier
    ) -> tuple[str, ApiKey]:
        raw = ApiKeyService.PREFIX + secrets.token_urlsafe(32)
        entity = ApiKey(
            id=uuid4(),
            user_id=user_id,
            name=name,
            key_hash=TokenService.hash_token(raw),
            prefix=raw[:12],
            scopes=scopes,
            rate_limit_tier=tier,
        )
        return raw, entity

    @staticmethod
    def hash_key(raw: str) -> str:
        return TokenService.hash_token(raw)


async def resolve_api_key(
    api_key_repo: ApiKeyRepository,
    raw_key: str,
) -> tuple[UUID, ApiKey]:
    if not raw_key.startswith(ApiKeyService.PREFIX):
        raise AuthenticationError("Invalid API key format")
    key_hash = ApiKeyService.hash_key(raw_key)
    stored = await api_key_repo.get_by_hash(key_hash)
    if not stored or not stored.is_valid:
        raise AuthenticationError("Invalid or revoked API key")
    await api_key_repo.touch_last_used(stored.id)
    return stored.user_id, stored


async def find_or_create_oauth_user(
    user_repo: UserRepository,
    role_repo: RoleRepository,
    oauth_repo: OAuthAccountRepository,
    provider: OAuthProvider,
    info: OAuthUserInfo,
) -> User:
    existing_oauth = await oauth_repo.get_by_provider_uid(provider.value, info.provider_uid)
    if existing_oauth:
        user = await user_repo.get_by_id(existing_oauth.user_id)
        if user:
            return user

    user = await user_repo.get_by_email(info.email)
    if not user:
        user = User.create(info.email, password_hash=None, display_name=info.display_name)
        user.email_verified = True
        default_roles = await role_repo.get_default_roles()
        user.roles = default_roles
        saved = await user_repo.save(user)
        for role in default_roles:
            await role_repo.assign_role(saved.id, role.id)
        user = saved

    account = OAuthAccount(
        id=uuid4(),
        user_id=user.id,
        provider=provider,
        provider_uid=info.provider_uid,
        email=info.email,
    )
    await oauth_repo.save(account)
    return user


async def issue_token_pair(
    user: User,
    token_repo: RefreshTokenRepository,
) -> tuple[str, str]:
    access_token = TokenService.create_access_token(str(user.id))
    raw_refresh, refresh_entity = TokenService.build_refresh_token(user.id)
    await token_repo.save(refresh_entity)
    return access_token, raw_refresh
