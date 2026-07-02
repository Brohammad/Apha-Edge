import math
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskMetricsResult:
    var_95: Decimal | None
    var_99: Decimal | None
    max_drawdown: Decimal
    sharpe_ratio: Decimal | None
    sortino_ratio: Decimal | None
    beta: Decimal | None
    alpha: Decimal | None
    volatility: Decimal | None
    correlation_matrix: dict[str, object] | None
    metrics: dict[str, object]


class RiskCalculator:
    """Institutional-style risk metrics from return series."""

    @staticmethod
    def compute(
        portfolio_returns: list[float],
        benchmark_returns: list[float] | None = None,
        *,
        equity_curve: list[float] | None = None,
    ) -> RiskMetricsResult:
        if not portfolio_returns:
            return RiskMetricsResult(
                var_95=None,
                var_99=None,
                max_drawdown=Decimal("0"),
                sharpe_ratio=None,
                sortino_ratio=None,
                beta=None,
                alpha=None,
                volatility=None,
                correlation_matrix=None,
                metrics={"sample_size": 0},
            )

        sorted_returns = sorted(portfolio_returns)
        n = len(sorted_returns)
        var_95 = RiskCalculator._historical_var(sorted_returns, 0.05)
        var_99 = RiskCalculator._historical_var(sorted_returns, 0.01)
        sharpe = RiskCalculator._sharpe(portfolio_returns)
        sortino = RiskCalculator._sortino(portfolio_returns)
        vol = RiskCalculator._volatility(portfolio_returns)
        max_dd = RiskCalculator._max_drawdown_from_returns(portfolio_returns, equity_curve)

        beta, alpha = None, None
        if benchmark_returns and len(benchmark_returns) == len(portfolio_returns):
            beta_f, alpha_f = RiskCalculator._beta_alpha(portfolio_returns, benchmark_returns)
            beta = Decimal(str(round(beta_f, 4))) if beta_f is not None else None
            alpha = Decimal(str(round(alpha_f, 4))) if alpha_f is not None else None

        corr = None
        if benchmark_returns and len(benchmark_returns) >= 2:
            corr = {
                "portfolio_benchmark": round(
                    RiskCalculator._correlation(portfolio_returns, benchmark_returns), 4
                )
            }

        return RiskMetricsResult(
            var_95=Decimal(str(round(var_95, 6))) if var_95 is not None else None,
            var_99=Decimal(str(round(var_99, 6))) if var_99 is not None else None,
            max_drawdown=Decimal(str(round(max_dd, 4))),
            sharpe_ratio=Decimal(str(round(sharpe, 4))) if sharpe is not None else None,
            sortino_ratio=Decimal(str(round(sortino, 4))) if sortino is not None else None,
            beta=beta,
            alpha=alpha,
            volatility=Decimal(str(round(vol, 4))) if vol is not None else None,
            correlation_matrix=corr,
            metrics={"sample_size": n, "mean_return": round(sum(portfolio_returns) / n, 6)},
        )

    @staticmethod
    def _historical_var(sorted_returns: list[float], tail: float) -> float | None:
        if not sorted_returns:
            return None
        idx = max(0, int(len(sorted_returns) * tail) - 1)
        return sorted_returns[idx]

    @staticmethod
    def _sharpe(returns: list[float], risk_free: float = 0.0) -> float | None:
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance)
        if std == 0:
            return None
        return (mean - risk_free) / std * math.sqrt(252)

    @staticmethod
    def _sortino(returns: list[float], risk_free: float = 0.0) -> float | None:
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        downside = [min(0.0, r - risk_free) ** 2 for r in returns]
        downside_dev = math.sqrt(sum(downside) / len(downside))
        if downside_dev == 0:
            return None
        return (mean - risk_free) / downside_dev * math.sqrt(252)

    @staticmethod
    def _volatility(returns: list[float]) -> float | None:
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        return math.sqrt(variance) * math.sqrt(252)

    @staticmethod
    def _max_drawdown_from_returns(returns: list[float], equity_curve: list[float] | None) -> float:
        if equity_curve and len(equity_curve) >= 2:
            peak = equity_curve[0]
            max_dd = 0.0
            for v in equity_curve:
                if v > peak:
                    peak = v
                if peak > 0:
                    max_dd = max(max_dd, (peak - v) / peak)
            return max_dd
        cumulative = 1.0
        peak = 1.0
        max_dd = 0.0
        for r in returns:
            cumulative *= 1.0 + r
            if cumulative > peak:
                peak = cumulative
            if peak > 0:
                max_dd = max(max_dd, (peak - cumulative) / peak)
        return max_dd

    @staticmethod
    def _beta_alpha(
        portfolio: list[float], benchmark: list[float]
    ) -> tuple[float | None, float | None]:
        if len(portfolio) < 2:
            return None, None
        n = len(portfolio)
        mean_p = sum(portfolio) / n
        mean_b = sum(benchmark) / n
        pairs = zip(portfolio, benchmark, strict=True)
        cov = sum((p - mean_p) * (b - mean_b) for p, b in pairs) / (n - 1)
        var_b = sum((b - mean_b) ** 2 for b in benchmark) / (n - 1)
        if var_b == 0:
            return None, None
        beta = cov / var_b
        alpha = (mean_p - beta * mean_b) * 252
        return beta, alpha

    @staticmethod
    def _correlation(a: list[float], b: list[float]) -> float:
        n = len(a)
        if n < 2:
            return 0.0
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True)) / (n - 1)
        std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / (n - 1))
        std_b = math.sqrt(sum((y - mean_b) ** 2 for y in b) / (n - 1))
        if std_a == 0 or std_b == 0:
            return 0.0
        return cov / (std_a * std_b)


class LimitEnforcer:
    """Check risk snapshots and holdings against configured limits."""

    @staticmethod
    def check(
        snapshot: RiskMetricsResult,
        limits: list,
        holdings: list,
        total_value: Decimal,
    ) -> list[dict[str, object]]:
        from alphaedge.modules.portfolio.domain.enums import RiskLimitType

        violations: list[dict[str, object]] = []
        for limit in limits:
            if not limit.is_active:
                continue
            if limit.limit_type == RiskLimitType.MAX_VAR:
                if snapshot.var_95 is not None and snapshot.var_95 > limit.threshold:
                    violations.append(
                        {
                            "limit_type": limit.limit_type.value,
                            "threshold": str(limit.threshold),
                            "actual": str(snapshot.var_95),
                            "message": "VaR 95% exceeds limit",
                        }
                    )
            elif limit.limit_type == RiskLimitType.MAX_DRAWDOWN:
                if snapshot.max_drawdown > limit.threshold:
                    violations.append(
                        {
                            "limit_type": limit.limit_type.value,
                            "threshold": str(limit.threshold),
                            "actual": str(snapshot.max_drawdown),
                            "message": "Max drawdown exceeds limit",
                        }
                    )
            elif limit.limit_type == RiskLimitType.MAX_POSITION_PCT and total_value > 0:
                for h in holdings:
                    pct = h.market_value / total_value
                    if pct > limit.threshold:
                        violations.append(
                            {
                                "limit_type": limit.limit_type.value,
                                "threshold": str(limit.threshold),
                                "actual": str(pct.quantize(Decimal("0.0001"))),
                                "instrument_id": str(h.instrument_id),
                                "message": "Position weight exceeds limit",
                            }
                        )
        return violations
