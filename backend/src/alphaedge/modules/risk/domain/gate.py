"""Pre-trade risk validation gate for paper (and live) order submission."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from alphaedge.modules.execution.domain.enums import ProductType
from alphaedge.modules.portfolio.domain.entities import Holding, Portfolio
from alphaedge.modules.portfolio.domain.enums import RiskLimitType
from alphaedge.modules.risk.domain.entities import RiskLimit, RiskSnapshot
from alphaedge.modules.risk.domain.mis_margin import estimate_required_margin
from alphaedge.shared.domain.value_objects import Side


@dataclass(frozen=True)
class ProposedOrder:
    instrument_id: UUID
    side: Side
    quantity: Decimal
    estimated_price: Decimal
    product_type: str = "CNC"


@dataclass(frozen=True)
class RiskGateResult:
    allowed: bool
    reason: str | None = None
    stage: str | None = None

    @staticmethod
    def ok() -> RiskGateResult:
        return RiskGateResult(allowed=True)

    @staticmethod
    def reject(stage: str, reason: str) -> RiskGateResult:
        return RiskGateResult(allowed=False, stage=stage, reason=reason)


class RiskGate:
    """Validate an order before it is persisted or sent to a broker.

    Pipeline:
      order → position sizing → max position exposure → portfolio exposure →
      cash availability → configured risk limits → daily loss limit
    """

    DEFAULT_MAX_POSITION_PCT = Decimal("1")
    DEFAULT_MAX_PORTFOLIO_EXPOSURE_PCT = Decimal("1")

    @classmethod
    def evaluate(
        cls,
        *,
        portfolio: Portfolio,
        holdings: list[Holding],
        proposed: ProposedOrder,
        limits: list[RiskLimit],
        latest_snapshot: RiskSnapshot | None = None,
    ) -> RiskGateResult:
        if proposed.quantity <= 0:
            return RiskGateResult.reject("position_sizing", "Order quantity must be positive")
        if proposed.estimated_price <= 0:
            return RiskGateResult.reject(
                "position_sizing",
                "Cannot estimate fill price for risk checks; ingest market data first",
            )

        order_notional = (proposed.quantity * proposed.estimated_price).quantize(Decimal("0.01"))
        current_equity = cls._equity(portfolio, holdings)
        projected_holdings = cls._project_holdings(portfolio.id, holdings, proposed)
        projected_cash = cls._project_cash(portfolio.cash_balance, proposed, order_notional)
        projected_equity = projected_cash + sum(
            (h.market_value for h in projected_holdings), Decimal("0")
        )

        max_position = cls._limit_value(limits, RiskLimitType.MAX_POSITION_PCT)
        if max_position is None:
            max_position = cls.DEFAULT_MAX_POSITION_PCT
        if projected_equity > 0:
            for holding in projected_holdings:
                if holding.instrument_id != proposed.instrument_id:
                    continue
                weight = holding.market_value / projected_equity
                if weight > max_position:
                    return RiskGateResult.reject(
                        "max_position_exposure",
                        f"Position would be {weight:.2%} of equity (limit {max_position:.2%})",
                    )

        max_exposure = cls._limit_value(limits, RiskLimitType.MAX_PORTFOLIO_EXPOSURE_PCT)
        if max_exposure is None:
            max_exposure = cls.DEFAULT_MAX_PORTFOLIO_EXPOSURE_PCT
        invested = sum((h.market_value for h in projected_holdings), Decimal("0"))
        if projected_equity > 0:
            exposure = invested / projected_equity
            if exposure > max_exposure:
                return RiskGateResult.reject(
                    "portfolio_exposure",
                    f"Portfolio exposure would be {exposure:.2%} (limit {max_exposure:.2%})",
                )

        if proposed.side == Side.BUY and order_notional > portfolio.cash_balance:
            required_cash = order_notional
            try:
                pt = ProductType(proposed.product_type.upper())
                required_cash = estimate_required_margin(
                    notional=order_notional, product_type=pt
                )
            except ValueError:
                pass
            if required_cash > portfolio.cash_balance:
                return RiskGateResult.reject(
                    "cash_availability",
                    f"Insufficient cash/margin: need {required_cash}, have {portfolio.cash_balance}",
                )

        if proposed.side == Side.SELL:
            held = next(
                (h for h in holdings if h.instrument_id == proposed.instrument_id),
                None,
            )
            held_qty = held.quantity if held else Decimal("0")
            if proposed.quantity > held_qty:
                return RiskGateResult.reject(
                    "position_sizing",
                    f"Cannot sell {proposed.quantity}; holding only {held_qty}",
                )

        for limit in limits:
            if not limit.is_active:
                continue
            if limit.limit_type == RiskLimitType.MAX_DRAWDOWN and latest_snapshot:
                dd = latest_snapshot.max_drawdown or Decimal("0")
                if dd > limit.threshold:
                    return RiskGateResult.reject(
                        "risk_limits",
                        f"Max drawdown {dd} exceeds limit {limit.threshold}",
                    )
            elif limit.limit_type == RiskLimitType.MAX_VAR and latest_snapshot:
                var95 = latest_snapshot.var_95
                if var95 is not None and abs(var95) > limit.threshold:
                    return RiskGateResult.reject(
                        "risk_limits",
                        f"VaR 95% {var95} exceeds limit {limit.threshold}",
                    )

        daily_loss = cls._limit_value(limits, RiskLimitType.DAILY_LOSS_PCT)
        if daily_loss is not None and current_equity > 0:
            reference = portfolio.initial_capital
            if latest_snapshot and isinstance(latest_snapshot.metrics, dict):
                sod = latest_snapshot.metrics.get("start_of_day_equity")
                if sod is not None:
                    with contextlib.suppress(Exception):
                        reference = Decimal(str(sod))
            if reference > 0:
                loss_pct = (reference - current_equity) / reference
                if loss_pct > daily_loss:
                    return RiskGateResult.reject(
                        "daily_loss_limit",
                        f"Daily loss {loss_pct:.2%} exceeds limit {daily_loss:.2%}",
                    )

        return RiskGateResult.ok()

    @staticmethod
    def _equity(portfolio: Portfolio, holdings: list[Holding]) -> Decimal:
        return portfolio.cash_balance + sum((h.market_value for h in holdings), Decimal("0"))

    @staticmethod
    def _limit_value(limits: list[RiskLimit], limit_type: RiskLimitType) -> Decimal | None:
        for limit in limits:
            if limit.is_active and limit.limit_type == limit_type:
                return limit.threshold
        return None

    @staticmethod
    def _project_cash(cash: Decimal, proposed: ProposedOrder, notional: Decimal) -> Decimal:
        if proposed.side == Side.BUY:
            return cash - notional
        return cash + notional

    @staticmethod
    def _project_holdings(
        portfolio_id: UUID,
        holdings: list[Holding],
        proposed: ProposedOrder,
    ) -> list[Holding]:
        projected: list[Holding] = []
        found = False
        delta = proposed.quantity if proposed.side == Side.BUY else -proposed.quantity
        for holding in holdings:
            if holding.instrument_id != proposed.instrument_id:
                projected.append(holding)
                continue
            found = True
            new_qty = holding.quantity + delta
            if new_qty <= 0:
                continue
            projected.append(
                Holding(
                    id=holding.id,
                    portfolio_id=holding.portfolio_id,
                    instrument_id=holding.instrument_id,
                    quantity=new_qty,
                    avg_cost=holding.avg_cost,
                    current_price=proposed.estimated_price,
                    market_value=new_qty * proposed.estimated_price,
                )
            )
        if not found and proposed.side == Side.BUY:
            projected.append(
                Holding(
                    id=uuid4(),
                    portfolio_id=portfolio_id,
                    instrument_id=proposed.instrument_id,
                    quantity=proposed.quantity,
                    avg_cost=proposed.estimated_price,
                    current_price=proposed.estimated_price,
                    market_value=proposed.quantity * proposed.estimated_price,
                )
            )
        return projected
