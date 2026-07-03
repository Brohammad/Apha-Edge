import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from alphaedge.config import settings
from alphaedge.modules.identity.domain.entities import RefreshToken
from alphaedge.shared.domain.exceptions import AuthenticationError


class PasswordService:
    @staticmethod
    def hash(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())


class TokenService:
    @staticmethod
    def create_access_token(user_id: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def create_refresh_token_value() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def decode_access_token(token: str) -> dict[str, str | list[str]]:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "access":
                raise AuthenticationError("Invalid token type")
            return payload
        except InvalidTokenError as e:
            raise AuthenticationError("Invalid or expired token") from e

    @staticmethod
    def build_refresh_token(user_id: UUID) -> tuple[str, RefreshToken]:
        raw_token = TokenService.create_refresh_token_value()
        expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
        entity = RefreshToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=TokenService.hash_token(raw_token),
            expires_at=expires_at,
        )
        return raw_token, entity

    @staticmethod
    def create_email_verification_token() -> tuple[str, str]:
        raw = secrets.token_urlsafe(32)
        return raw, TokenService.hash_token(raw)
