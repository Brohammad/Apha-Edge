"""Broker credential schemas and validation."""

from typing import Any

from pydantic import BaseModel, Field

from alphaedge.modules.execution.domain.enums import BrokerName
from alphaedge.shared.domain.exceptions import ValidationError


class PaperCredentials(BaseModel):
    pass


class AlpacaCredentials(BaseModel):
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
    base_url: str | None = None


class IbkrCredentials(BaseModel):
    account_id: str = Field(min_length=1)
    host: str = "127.0.0.1"
    port: int = 7497


class ZerodhaCredentials(BaseModel):
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
    access_token: str = ""
    request_token: str = ""


def validate_broker_credentials(
    broker_name: BrokerName, credentials: dict[str, Any]
) -> dict[str, Any]:
    if broker_name == BrokerName.PAPER:
        return PaperCredentials().model_dump()
    if broker_name == BrokerName.ALPACA:
        return AlpacaCredentials.model_validate(credentials).model_dump()
    if broker_name == BrokerName.IBKR:
        return IbkrCredentials.model_validate(credentials).model_dump()
    if broker_name == BrokerName.ZERODHA:
        return ZerodhaCredentials.model_validate(credentials).model_dump()
    raise ValidationError(f"Unsupported broker: {broker_name.value}")
