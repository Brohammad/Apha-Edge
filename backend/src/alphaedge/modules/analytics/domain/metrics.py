"""Portfolio analytics — extended risk/return metrics."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExtendedMetrics:
    factor_exposure: dict[str, Decimal]
    tracking_error: Decimal
    information_ratio: Decimal
    sharpe_ratio: Decimal | None = None


def compute_extended_metrics(
    returns: list[Decimal],
    benchmark_returns: list[Decimal] | None = None,
) -> ExtendedMetrics:
    if not returns:
        return ExtendedMetrics(
            factor_exposure={"market": Decimal("0")},
            tracking_error=Decimal("0"),
            information_ratio=Decimal("0"),
        )
    mean_ret = sum(returns) / len(returns)
    variance = sum((r - mean_ret) ** 2 for r in returns) / max(len(returns) - 1, 1)
    vol = variance.sqrt() if hasattr(variance, "sqrt") else Decimal(str(float(variance) ** 0.5))
    te = Decimal("0")
    ir = Decimal("0")
    if benchmark_returns and len(benchmark_returns) == len(returns):
        diffs = [r - b for r, b in zip(returns, benchmark_returns, strict=True)]
        te = (sum(d**2 for d in diffs) / len(diffs)).sqrt() if hasattr(sum(d**2 for d in diffs), "sqrt") else Decimal("0.05")
        ir = (mean_ret / te) if te > 0 else Decimal("0")
    return ExtendedMetrics(
        factor_exposure={"market": mean_ret, "momentum": vol},
        tracking_error=te,
        information_ratio=ir,
        sharpe_ratio=(mean_ret / vol) if vol > 0 else None,
    )
