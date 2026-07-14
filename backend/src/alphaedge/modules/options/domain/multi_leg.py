"""Multi-leg options strategies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.options.domain.instrument import OptionType, OptionsInstrument


@dataclass(frozen=True)
class OptionLeg:
    instrument: OptionsInstrument
    quantity: Decimal
    side: str  # buy | sell


@dataclass
class MultiLegStrategy:
    id: UUID
    name: str
    legs: list[OptionLeg]

    @staticmethod
    def create(name: str, legs: list[OptionLeg]) -> "MultiLegStrategy":
        return MultiLegStrategy(id=uuid4(), name=name, legs=legs)

    def net_delta(self, deltas: dict[UUID, Decimal]) -> Decimal:
        total = Decimal("0")
        for leg in self.legs:
            sign = Decimal("1") if leg.side == "buy" else Decimal("-1")
            total += sign * leg.quantity * deltas.get(leg.instrument.id, Decimal("0"))
        return total


def iron_condor(underlying_id: UUID, symbol: str) -> MultiLegStrategy:
    from datetime import date
    from decimal import Decimal

    expiry = date.today()
    legs = [
        OptionLeg(OptionsInstrument.create(underlying_id, f"{symbol}C100", Decimal("100"), expiry, OptionType.CALL), Decimal("1"), "sell"),
        OptionLeg(OptionsInstrument.create(underlying_id, f"{symbol}P90", Decimal("90"), expiry, OptionType.PUT), Decimal("1"), "sell"),
    ]
    return MultiLegStrategy.create("iron_condor", legs)
