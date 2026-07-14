"""Option chain snapshot service (synthetic data for Indian underlyings)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class OptionContract:
    symbol: str
    strike: Decimal
    option_type: str  # CE | PE
    expiry: date
    ltp: Decimal
    oi: int
    iv: Decimal | None = None


@dataclass(frozen=True)
class OptionChainSnapshot:
    underlying: str
    spot_price: Decimal
    as_of: datetime
    contracts: list[OptionContract]


def build_option_chain(underlying: str, spot: Decimal | None = None) -> OptionChainSnapshot:
    """Return a synthetic option chain around ATM strikes."""
    spot = spot or Decimal("2500")
    strikes = [spot - Decimal(s * 50) for s in range(3, 0, -1)]
    strikes.append(spot)
    strikes.extend(spot + Decimal(s * 50) for s in range(1, 4))
    expiry = date.today().replace(day=28) if date.today().day < 28 else date.today()
    contracts: list[OptionContract] = []
    for strike in strikes:
        for opt_type in ("CE", "PE"):
            moneyness = abs(strike - spot)
            ltp = max(Decimal("5"), (spot * Decimal("0.02")) - moneyness * Decimal("0.1"))
            contracts.append(
                OptionContract(
                    symbol=f"{underlying}{expiry.strftime('%y%b').upper()}{int(strike)}{opt_type}",
                    strike=strike,
                    option_type=opt_type,
                    expiry=expiry,
                    ltp=ltp.quantize(Decimal("0.05")),
                    oi=10000 + int(moneyness),
                    iv=Decimal("18.5"),
                )
            )
    return OptionChainSnapshot(
        underlying=underlying.upper(),
        spot_price=spot,
        as_of=datetime.now(UTC),
        contracts=contracts,
    )
