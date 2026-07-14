from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.modules.backtesting.infrastructure.models import (
    SQLAlchemyBacktestResultRepository,
    SQLAlchemyBacktestRunRepository,
    SQLAlchemyBacktestTradeRepository,
)
from alphaedge.modules.execution.infrastructure.models import (
    SQLAlchemyExecutionRepository,
    SQLAlchemyOrderRepository,
)
from alphaedge.modules.insights.domain.enums import InsightType, SourceType
from alphaedge.modules.portfolio.infrastructure.models import SQLAlchemyPortfolioRepository
from alphaedge.modules.risk.infrastructure.models import SQLAlchemyRiskSnapshotRepository
from alphaedge.modules.strategy.infrastructure.models import (
    SQLAlchemyStrategyRepository,
    SQLAlchemyStrategyVersionRepository,
)
from alphaedge.modules.insights.infrastructure.tavily_research import get_research_provider
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


async def build_context(
    session: AsyncSession,
    *,
    user_id: UUID,
    insight_type: InsightType,
    source_type: SourceType,
    source_id: UUID,
) -> dict[str, object]:
    if insight_type == InsightType.STRATEGY_EXPLANATION:
        return await _strategy_context(session, user_id, source_type, source_id)
    if insight_type == InsightType.PERFORMANCE_REPORT:
        return await _performance_context(session, user_id, source_id)
    if insight_type == InsightType.RISK_INTERPRETATION:
        return await _risk_context(session, user_id, source_id)
    if insight_type == InsightType.TRADE_SUMMARY:
        return await _trade_context(session, user_id, source_type, source_id)
    if insight_type == InsightType.COMPANY_RESEARCH:
        return await _company_research_context(session, user_id, source_type, source_id)
    raise ValidationError(f"Unsupported insight type: {insight_type.value}")


async def _enrich_with_research(context: dict[str, object], query: str) -> dict[str, object]:
    provider = get_research_provider()
    result = await provider.search(query)
    enriched = dict(context)
    enriched["research_summary"] = result.summary
    enriched["research_sources"] = result.sources
    return enriched


async def _strategy_context(
    session: AsyncSession,
    user_id: UUID,
    source_type: SourceType,
    source_id: UUID,
) -> dict[str, object]:
    strategy_repo = SQLAlchemyStrategyRepository(session)
    version_repo = SQLAlchemyStrategyVersionRepository(session)

    if source_type == SourceType.STRATEGY_VERSION:
        version = await version_repo.get_by_id(source_id)
        if not version:
            raise NotFoundError("StrategyVersion", str(source_id))
        strategy = await strategy_repo.get_by_id(version.strategy_id)
    elif source_type == SourceType.STRATEGY:
        strategy = await strategy_repo.get_by_id(source_id)
        if not strategy:
            raise NotFoundError("Strategy", str(source_id))
        versions = await version_repo.list_by_strategy(strategy.id)
        version = versions[0] if versions else None
    else:
        raise ValidationError("strategy_explanation requires strategy or strategy_version source")

    if not strategy or strategy.deleted_at is not None:
        raise NotFoundError("Strategy", str(source_id))
    if strategy.user_id != user_id:
        raise AuthorizationError("You do not own this strategy")
    if not version:
        raise NotFoundError("StrategyVersion", str(source_id))

    return await _enrich_with_research(
        {
            "strategy_name": strategy.name,
            "strategy_type": strategy.strategy_type.value,
            "parameters": version.parameters,
            "source_code": version.source_code,
        },
        query=f"{strategy.name} company fundamentals news",
    )


async def _performance_context(
    session: AsyncSession,
    user_id: UUID,
    backtest_run_id: UUID,
) -> dict[str, object]:
    run_repo = SQLAlchemyBacktestRunRepository(session)
    result_repo = SQLAlchemyBacktestResultRepository(session)

    run = await run_repo.get_by_id(backtest_run_id)
    if not run:
        raise NotFoundError("BacktestRun", str(backtest_run_id))
    if run.user_id != user_id:
        raise AuthorizationError("You do not own this backtest run")

    result = await result_repo.get_by_run_id(backtest_run_id)
    if not result:
        raise NotFoundError("BacktestResult", str(backtest_run_id))

    config = run.config
    curve = result.equity_curve
    equity_summary = "flat"
    if len(curve) >= 2:
        start_eq = curve[0].get("equity", 0)
        end_eq = curve[-1].get("equity", 0)
        equity_summary = f"{start_eq} → {end_eq} over {len(curve)} points"

    return {
        "backtest_name": run.name,
        "start_date": config.get("start_date", "unknown"),
        "end_date": config.get("end_date", "unknown"),
        "total_return": result.total_return,
        "sharpe_ratio": result.sharpe_ratio or "N/A",
        "max_drawdown": result.max_drawdown,
        "win_rate": result.win_rate or "N/A",
        "total_trades": result.total_trades,
        "equity_summary": equity_summary,
    }


async def _risk_context(
    session: AsyncSession,
    user_id: UUID,
    snapshot_id: UUID,
) -> dict[str, object]:
    snapshot_repo = SQLAlchemyRiskSnapshotRepository(session)
    portfolio_repo = SQLAlchemyPortfolioRepository(session)

    snapshot = await snapshot_repo.get_by_id(snapshot_id)
    if not snapshot:
        raise NotFoundError("RiskSnapshot", str(snapshot_id))
    portfolio = await portfolio_repo.get_by_id(snapshot.portfolio_id)
    if not portfolio or portfolio.user_id != user_id:
        raise AuthorizationError("You do not own this risk snapshot")

    return {
        "portfolio_id": snapshot.portfolio_id,
        "snapshot_at": snapshot.snapshot_at.isoformat(),
        "var_95": snapshot.var_95 or "N/A",
        "var_99": snapshot.var_99 or "N/A",
        "max_drawdown": snapshot.max_drawdown or "N/A",
        "sharpe_ratio": snapshot.sharpe_ratio or "N/A",
        "beta": snapshot.beta or "N/A",
        "alpha": snapshot.alpha or "N/A",
        "volatility": snapshot.volatility or "N/A",
    }


async def _trade_context(
    session: AsyncSession,
    user_id: UUID,
    source_type: SourceType,
    source_id: UUID,
) -> dict[str, object]:
    if source_type == SourceType.BACKTEST:
        run_repo = SQLAlchemyBacktestRunRepository(session)
        trade_repo = SQLAlchemyBacktestTradeRepository(session)
        run = await run_repo.get_by_id(source_id)
        if not run:
            raise NotFoundError("BacktestRun", str(source_id))
        if run.user_id != user_id:
            raise AuthorizationError("You do not own this backtest run")
        trades = await trade_repo.list_by_run_id(source_id)
        lines = [f"- {t.side} {t.quantity}@{t.entry_price} pnl={t.pnl}" for t in trades[:50]]
        return {
            "source_label": f"backtest {run.name}",
            "trade_count": len(trades),
            "trades_text": "\n".join(lines) if lines else "No trades recorded.",
        }

    if source_type == SourceType.ORDER:
        order_repo = SQLAlchemyOrderRepository(session)
        execution_repo = SQLAlchemyExecutionRepository(session)
        portfolio_repo = SQLAlchemyPortfolioRepository(session)
        order = await order_repo.get_by_id(source_id)
        if not order:
            raise NotFoundError("Order", str(source_id))
        portfolio = await portfolio_repo.get_by_id(order.portfolio_id)
        if not portfolio or portfolio.user_id != user_id:
            raise AuthorizationError("You do not own this order")
        executions = await execution_repo.list_by_order_id(source_id)
        lines = [f"- fill {e.quantity}@{e.price} comm={e.commission}" for e in executions]
        return {
            "source_label": f"order {order.id}",
            "trade_count": len(executions),
            "trades_text": "\n".join(lines) if lines else "No executions recorded.",
        }

    raise ValidationError("trade_summary requires backtest or order source")


async def _company_research_context(
    session: AsyncSession,
    user_id: UUID,
    source_type: SourceType,
    source_id: UUID,
) -> dict[str, object]:
    from alphaedge.modules.market_data.infrastructure.models import SQLAlchemyInstrumentRepository

    if source_type != SourceType.INSTRUMENT:
        raise ValidationError("company_research requires instrument source")

    repo = SQLAlchemyInstrumentRepository(session)
    instrument = await repo.get_by_id(source_id)
    if not instrument:
        raise NotFoundError("Instrument", str(source_id))

    base = {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "exchange": instrument.exchange,
        "currency": instrument.currency,
    }
    return await _enrich_with_research(
        base,
        query=f"{instrument.name} ({instrument.symbol}) stock analysis recent news",
    )
