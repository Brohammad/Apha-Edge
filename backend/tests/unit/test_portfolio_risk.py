from decimal import Decimal
from uuid import uuid4

from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio
from alphaedge.modules.portfolio.domain.services import PerformanceCalculator, Rebalancer
from alphaedge.modules.risk.domain.metrics import LimitEnforcer, RiskCalculator


class TestRiskCalculator:
    def test_var_sharpe_and_drawdown(self):
        returns = [0.01, -0.02, 0.015, -0.005, 0.02, -0.01, 0.005, 0.008, -0.015, 0.012]
        result = RiskCalculator.compute(returns)
        assert result.var_95 is not None
        assert result.var_99 is not None
        assert result.max_drawdown >= Decimal("0")
        assert result.sharpe_ratio is not None
        assert result.volatility is not None

    def test_beta_alpha_with_benchmark(self):
        port = [0.01, 0.02, -0.01, 0.015, -0.005]
        bench = [0.008, 0.015, -0.008, 0.01, -0.003]
        result = RiskCalculator.compute(port, bench)
        assert result.beta is not None
        assert result.alpha is not None
        assert result.correlation_matrix is not None

    def test_empty_returns(self):
        result = RiskCalculator.compute([])
        assert result.max_drawdown == Decimal("0")
        assert result.var_95 is None


class TestLimitEnforcer:
    def test_max_drawdown_violation(self):
        from alphaedge.modules.portfolio.domain.enums import RiskLimitType
        from alphaedge.modules.risk.domain.entities import RiskLimit

        metrics = RiskCalculator.compute([0.05, -0.15, 0.02, -0.10, 0.01])
        limit = RiskLimit.create(uuid4(), RiskLimitType.MAX_DRAWDOWN, Decimal("0.05"))
        violations = LimitEnforcer.check(metrics, [limit], [], Decimal("100000"))
        assert any(v["limit_type"] == "max_drawdown" for v in violations)


class TestRebalancer:
    def test_generates_trades_toward_target(self):
        pid = uuid4()
        iid = uuid4()
        portfolio = Portfolio.create(uuid4(), "Test", Decimal("100000"))
        holdings = [
            Holding.create(pid, iid, Decimal("100"), Decimal("50"), Decimal("60")),
        ]
        portfolio.cash_balance = Decimal("94000")
        trades = Rebalancer.generate(
            portfolio,
            holdings,
            {"AAPL": 0.5, "MSFT": 0.5},
            symbol_by_instrument={iid: "AAPL"},
        )
        assert isinstance(trades, list)


class TestPerformanceCalculator:
    def test_total_return(self):
        portfolio = Portfolio.create(uuid4(), "Perf", Decimal("100000"))
        portfolio.cash_balance = Decimal("50000")
        holdings = [
            Holding.create(uuid4(), uuid4(), Decimal("500"), Decimal("100"), Decimal("110")),
        ]
        summary = PerformanceCalculator.summarize(portfolio, holdings)
        assert float(summary["total_return"]) > 0
        assert summary["holdings_count"] == 1
