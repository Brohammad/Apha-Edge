"""Unit tests for the pre-trade RiskGate."""

from decimal import Decimal
from uuid import uuid4

from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio
from alphaedge.modules.portfolio.domain.enums import RiskLimitType
from alphaedge.modules.risk.domain.entities import RiskLimit
from alphaedge.modules.risk.domain.gate import ProposedOrder, RiskGate
from alphaedge.shared.domain.value_objects import Side


def _portfolio(cash: Decimal = Decimal("100000")) -> Portfolio:
    p = Portfolio.create(uuid4(), "Test Portfolio", cash)
    p.cash_balance = cash
    return p


def _holding(portfolio_id, instrument_id, qty: Decimal, price: Decimal) -> Holding:
    return Holding(
        id=uuid4(),
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        quantity=qty,
        avg_cost=price,
        current_price=price,
        market_value=qty * price,
    )


def _limit(limit_type: RiskLimitType, threshold: Decimal) -> RiskLimit:
    return RiskLimit.create(uuid4(), limit_type, threshold)


class TestRiskGateCashRejection:
    def test_rejects_buy_when_insufficient_cash(self):
        # Pipeline order: max_position → portfolio_exposure → cash_availability.
        # To isolate the cash_availability stage we must pass the earlier checks.
        # Set MAX_PORTFOLIO_EXPOSURE_PCT to 200% so that check is bypassed, then
        # cash < notional triggers the cash gate.
        portfolio = _portfolio(cash=Decimal("500"))
        instrument_id = uuid4()
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.BUY,
            quantity=Decimal("10"),
            estimated_price=Decimal("100"),  # notional = 1000 > cash 500
        )
        # Both max_position and portfolio_exposure checks come before cash_availability
        # in the pipeline. Pass both by setting high limits so cash_availability fires.
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[
                _limit(RiskLimitType.MAX_POSITION_PCT, Decimal("5.0")),
                _limit(RiskLimitType.MAX_PORTFOLIO_EXPOSURE_PCT, Decimal("5.0")),
            ],
        )
        assert not result.allowed
        assert result.stage == "cash_availability"

    def test_allows_buy_when_enough_cash(self):
        portfolio = _portfolio(cash=Decimal("10000"))
        instrument_id = uuid4()
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.BUY,
            quantity=Decimal("10"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[],
        )
        assert result.allowed


class TestRiskGateMaxPositionRejection:
    def test_rejects_when_position_exceeds_max_pct(self):
        portfolio = _portfolio(cash=Decimal("5000"))
        instrument_id = uuid4()
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.BUY,
            quantity=Decimal("50"),
            estimated_price=Decimal("100"),
        )
        # 50 * 100 = 5000; total equity = 5000 cash - 5000 order + 5000 position = 5000
        # weight = 5000/5000 = 100% > 20% limit
        limit = _limit(RiskLimitType.MAX_POSITION_PCT, Decimal("0.20"))
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[limit],
        )
        assert not result.allowed
        assert result.stage == "max_position_exposure"


class TestRiskGateDailyLossRejection:
    def test_rejects_when_daily_loss_exceeds_limit(self):
        import datetime

        from alphaedge.modules.risk.domain.entities import RiskSnapshot

        portfolio = _portfolio(cash=Decimal("80000"))
        portfolio.initial_capital = Decimal("100000")

        snapshot = RiskSnapshot(
            id=uuid4(),
            portfolio_id=portfolio.id,
            snapshot_at=datetime.datetime.now(datetime.UTC),
            metrics={"start_of_day_equity": "100000"},
            max_drawdown=Decimal("0"),
            var_95=None,
            var_99=None,
            sharpe_ratio=None,
            sortino_ratio=None,
            volatility=None,
            beta=None,
            alpha=None,
            correlation_matrix=None,
        )

        limit = _limit(RiskLimitType.DAILY_LOSS_PCT, Decimal("0.05"))
        instrument_id = uuid4()
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.BUY,
            quantity=Decimal("1"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[limit],
            latest_snapshot=snapshot,
        )
        assert not result.allowed
        assert result.stage == "daily_loss_limit"


class TestRiskGateSellWithoutHolding:
    def test_rejects_sell_when_not_holding(self):
        portfolio = _portfolio(cash=Decimal("10000"))
        instrument_id = uuid4()
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.SELL,
            quantity=Decimal("10"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[],
        )
        assert not result.allowed
        assert result.stage == "position_sizing"

    def test_rejects_sell_when_quantity_exceeds_holding(self):
        portfolio = _portfolio(cash=Decimal("10000"))
        instrument_id = uuid4()
        holdings = [_holding(portfolio.id, instrument_id, Decimal("5"), Decimal("100"))]
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.SELL,
            quantity=Decimal("10"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=holdings,
            proposed=proposed,
            limits=[],
        )
        assert not result.allowed
        assert result.stage == "position_sizing"


class TestRiskGateHappyPath:
    def test_allows_valid_buy(self):
        portfolio = _portfolio(cash=Decimal("50000"))
        instrument_id = uuid4()
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.BUY,
            quantity=Decimal("10"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[],
        )
        assert result.allowed
        assert result.reason is None

    def test_allows_valid_sell(self):
        portfolio = _portfolio(cash=Decimal("10000"))
        instrument_id = uuid4()
        holdings = [_holding(portfolio.id, instrument_id, Decimal("20"), Decimal("100"))]
        proposed = ProposedOrder(
            instrument_id=instrument_id,
            side=Side.SELL,
            quantity=Decimal("10"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=holdings,
            proposed=proposed,
            limits=[],
        )
        assert result.allowed

    def test_rejects_zero_quantity(self):
        portfolio = _portfolio(cash=Decimal("10000"))
        proposed = ProposedOrder(
            instrument_id=uuid4(),
            side=Side.BUY,
            quantity=Decimal("0"),
            estimated_price=Decimal("100"),
        )
        result = RiskGate.evaluate(
            portfolio=portfolio,
            holdings=[],
            proposed=proposed,
            limits=[],
        )
        assert not result.allowed
        assert result.stage == "position_sizing"
