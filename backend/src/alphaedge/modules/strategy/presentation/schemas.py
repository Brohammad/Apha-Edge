from datetime import datetime

from pydantic import BaseModel, Field


class CreateStrategyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    strategy_type: str = Field(pattern="^(python|dsl)$")
    description: str | None = None
    source_code: str | None = None
    parameters: dict[str, object] | None = None


class UpdateStrategyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class CreateStrategyVersionRequest(BaseModel):
    source_code: str = Field(min_length=1)
    parameters: dict[str, object] | None = None


class StrategyResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None
    strategy_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StrategyVersionResponse(BaseModel):
    id: str
    strategy_id: str
    version: int
    source_code: str
    parameters: dict[str, object]
    compiled_hash: str | None
    status: str
    created_at: datetime


class IndicatorResponse(BaseModel):
    id: str
    name: str
    category: str
    parameters_schema: dict[str, object]
    implementation: str


class ValidationResultResponse(BaseModel):
    version_id: str
    status: str
    compiled_hash: str
    errors: list[str]
