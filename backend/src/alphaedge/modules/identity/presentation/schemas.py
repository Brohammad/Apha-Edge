from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    roles: list[str]
    is_active: bool


class MetaResponse(BaseModel):
    request_id: str


class EnvelopeResponse(BaseModel):
    data: dict
    meta: MetaResponse


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class CreateApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=lambda: ["read:*", "write:*"])
    rate_limit_tier: str = "standard"


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    prefix: str
    scopes: list[str]
    rate_limit_tier: str
    created_at: object
    last_used_at: object | None = None


class CreateApiKeyResponse(BaseModel):
    api_key: ApiKeyResponse
    key: str
