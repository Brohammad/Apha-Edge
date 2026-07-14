"""Options Greeks calculator."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Greeks:
    delta: Decimal
    gamma: Decimal
    theta: Decimal
    vega: Decimal


def black_scholes_greeks(
    *,
    spot: float,
    strike: float,
    t_years: float,
    rate: float,
    vol: float,
    is_call: bool,
) -> Greeks:
    if t_years <= 0 or vol <= 0:
        return Greeks(Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"))
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol**2) * t_years) / (vol * math.sqrt(t_years))
    d2 = d1 - vol * math.sqrt(t_years)
    from math import erf, exp, sqrt, pi

    def cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    pdf = math.exp(-0.5 * d1 * d1) / sqrt(2 * pi)
    delta = cdf(d1) if is_call else cdf(d1) - 1
    gamma = pdf / (spot * vol * sqrt(t_years))
    theta = -(spot * pdf * vol) / (2 * sqrt(t_years))
    vega = spot * pdf * sqrt(t_years)
    return Greeks(
        delta=Decimal(str(round(delta, 6))),
        gamma=Decimal(str(round(gamma, 6))),
        theta=Decimal(str(round(theta, 6))),
        vega=Decimal(str(round(vega, 6))),
    )
