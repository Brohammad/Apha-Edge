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

    # Trust X-Forwarded-For only when the app sits behind a reverse proxy (e.g. Nginx).
    trust_proxy_headers: bool = False

    # Protect /api/v1/metrics in production (Bearer token or X-Metrics-Key header).
    metrics_api_key: str = ""

    # Fernet-compatible secret for encrypting broker credentials at rest.
    credentials_encryption_key: str = ""

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
    quote_provider: Literal["auto", "polygon", "alpha_vantage"] = "auto"

    # C++ backtest engine: "auto" uses it when installed, "off" forces the
    # Python path, "require" fails if the extension is missing.
    cpp_engine: Literal["auto", "off", "require"] = "auto"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    llm_provider: Literal["mock", "openai"] = "openai"

    # Tavily research
    tavily_api_key: str = ""
    research_provider: Literal["mock", "tavily"] = "mock"

    # SEC EDGAR
    sec_user_agent: str = "AlphaEdge research@example.com"

    # OpenTelemetry
    otel_enabled: bool = False

    # Crypto brokers
    binance_api_key: str = ""
    binance_api_secret: str = ""
    coinbase_api_key: str = ""
    coinbase_api_secret: str = ""

    # OAuth (Google, GitHub)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    github_oauth_client_id: str = ""
    github_oauth_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:8000/api/v1/auth/oauth"
    oauth_frontend_callback_url: str = "http://localhost:5173/oauth/callback"

    # Alpaca broker
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_paper_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_live_base_url: str = "https://api.alpaca.markets"

    # Indian brokers
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""
    angelone_api_key: str = ""
    upstox_api_key: str = ""
    upstox_api_secret: str = ""

    # Indian market data provider: mock | indian
    indian_market_data_provider: str = "mock"

    # Rate limiting (Redis sliding window)
    rate_limit_enabled: bool = True

    # Live trading (disabled by default — must be explicitly enabled in production)
    live_trading_enabled: bool = False

    # Python strategy sandbox (trusted single-tenant; see docs/STRATEGY_SANDBOX.md)
    strategy_exec_timeout_seconds: float = 5.0
    strategy_load_timeout_seconds: float = 10.0
    strategy_memory_limit_mb: int = 512

    # Risk snapshot Redis cache TTL (seconds)
    risk_snapshot_cache_ttl_seconds: int = 60

    # Stripe marketplace payments
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    @property
    def is_testing(self) -> bool:
        return self.app_env in ("test", "testing")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env in ("development", "dev", "local")

    def validate_security(self) -> None:
        """Fail fast when unsafe defaults would reach a deployed environment."""
        if self.is_testing or self.is_development:
            return

        unsafe: list[str] = []
        if self.jwt_secret_key in ("", "change-me-jwt"):
            unsafe.append("JWT_SECRET_KEY")
        if self.app_secret_key in ("", "change-me"):
            unsafe.append("APP_SECRET_KEY")
        if "alphaedge:alphaedge@" in self.database_url:
            unsafe.append("DATABASE_URL (default credentials)")
        if self.live_trading_enabled and not self.credentials_encryption_key:
            unsafe.append("CREDENTIALS_ENCRYPTION_KEY (required for live trading)")
        if unsafe:
            raise RuntimeError(
                "Refusing to start: insecure configuration for "
                f"APP_ENV={self.app_env!r}: {', '.join(unsafe)}"
            )


settings = Settings()
