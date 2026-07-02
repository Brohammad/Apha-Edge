from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(_REPO_ROOT / ".env"),
            str(_BACKEND_ROOT / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://alphaedge:alphaedge@localhost:5432/alphaedge"
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"

    alpha_vantage_api_key: str = ""
    polygon_api_key: str = ""

    # C++ backtest engine: "auto" uses it when installed, "off" forces the
    # Python path, "require" fails if the extension is missing.
    cpp_engine: Literal["auto", "off", "require"] = "auto"

    openai_api_key: str = ""
    llm_provider: Literal["mock", "openai"] = "mock"


settings = Settings()
