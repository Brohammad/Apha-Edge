from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.backtesting.domain.enums import (
    PositionSizingModel,
    SlippageModel,
)
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass(frozen=True)
class SlippageConfig:
    model: SlippageModel
    value: Decimal


@dataclass(frozen=True)
class CommissionConfig:
    per_trade: Decimal


@dataclass(frozen=True)
class PositionSizingConfig:
    model: PositionSizingModel
    value: Decimal


@dataclass(frozen=True)
class BacktestConfig:
    instrument_ids: list[UUID]
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    slippage: SlippageConfig
    commission: CommissionConfig
    position_sizing: PositionSizingConfig
    partial_fill_ratio: Decimal = Decimal("1")
    allow_short: bool = False

    @staticmethod
    def from_dict(data: dict[str, object]) -> "BacktestConfig":
        if not data.get("instrument_ids"):
            raise ValidationError("At least one instrument_id is required")
        instrument_ids = [UUID(str(i)) for i in data["instrument_ids"]]  # type: ignore[index]
        start = data.get("start_date")
        end = data.get("end_date")
        if not start or not end:
            raise ValidationError("start_date and end_date are required")
        start_date = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        if start_date >= end_date:
            raise ValidationError("start_date must be before end_date")

        slippage_raw = data.get("slippage") or {"model": "fixed", "value": 0}
        commission_raw = data.get("commission") or {"per_trade": 0}
        sizing_raw = data.get("position_sizing") or {
            "model": "percent_equity",
            "value": 0.1,
        }

        return BacktestConfig(
            instrument_ids=instrument_ids,
            timeframe=str(data.get("timeframe", "1d")),
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal(str(data.get("initial_capital", 100_000))),
            slippage=SlippageConfig(
                model=SlippageModel(str(slippage_raw.get("model", "fixed"))),  # type: ignore[union-attr]
                value=Decimal(str(slippage_raw.get("value", 0))),  # type: ignore[union-attr]
            ),
            commission=CommissionConfig(
                per_trade=Decimal(str(commission_raw.get("per_trade", 0))),  # type: ignore[union-attr]
            ),
            position_sizing=PositionSizingConfig(
                model=PositionSizingModel(str(sizing_raw.get("model", "percent_equity"))),  # type: ignore[union-attr]
                value=Decimal(str(sizing_raw.get("value", 0.1))),  # type: ignore[union-attr]
            ),
            partial_fill_ratio=Decimal(str(data.get("partial_fill_ratio", 1))),
            allow_short=bool(data.get("allow_short", False)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "instrument_ids": [str(i) for i in self.instrument_ids],
            "timeframe": self.timeframe,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "initial_capital": str(self.initial_capital),
            "slippage": {"model": self.slippage.model.value, "value": str(self.slippage.value)},
            "commission": {"per_trade": str(self.commission.per_trade)},
            "position_sizing": {
                "model": self.position_sizing.model.value,
                "value": str(self.position_sizing.value),
            },
            "partial_fill_ratio": str(self.partial_fill_ratio),
            "allow_short": self.allow_short,
        }
