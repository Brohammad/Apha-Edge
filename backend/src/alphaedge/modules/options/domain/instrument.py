"""Options instrument domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True)
class OptionsInstrument:
    id: UUID
    underlying_id: UUID
    symbol: str
    strike: Decimal
    expiry: date
    option_type: OptionType
    multiplier: Decimal = Decimal("100")

    @staticmethod
    def create(
        underlying_id: UUID,
        symbol: str,
        strike: Decimal,
        expiry: date,
        option_type: OptionType,
    ) -> "OptionsInstrument":
        return OptionsInstrument(
            id=uuid4(),
            underlying_id=underlying_id,
            symbol=symbol,
            strike=strike,
            expiry=expiry,
            option_type=option_type,
        )
