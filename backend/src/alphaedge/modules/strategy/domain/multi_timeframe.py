"""Multi-timeframe bar context for strategy runtime."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from alphaedge.modules.market_data.domain.enums import Timeframe


@dataclass(frozen=True)
class MultiTimeframeContext:
    primary: Timeframe
    bars: dict[Timeframe, list[dict[str, Decimal]]]

    def latest(self, tf: Timeframe) -> dict[str, Decimal] | None:
        series = self.bars.get(tf, [])
        return series[-1] if series else None

    def align(self, tf: Timeframe) -> list[dict[str, Decimal]]:
        return self.bars.get(tf, [])
