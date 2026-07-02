from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from alphaedge.modules.portfolio.domain.repositories import HoldingRepository, PortfolioRepository
from alphaedge.modules.risk.application.commands import (
    ComputeRiskCommand,
    GetLatestRiskSnapshotQuery,
    GetRiskLimitsQuery,
    ListRiskSnapshotsQuery,
    RiskLimitDTO,
    RiskSnapshotDTO,
    UpdateRiskLimitsCommand,
)
from alphaedge.modules.risk.domain.entities import RiskLimit, RiskSnapshot
from alphaedge.modules.risk.domain.metrics import LimitEnforcer, RiskCalculator
from alphaedge.modules.risk.domain.repositories import RiskLimitRepository, RiskSnapshotRepository
from alphaedge.modules.risk.domain.returns import ReturnSeriesBuilder
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError


async def _get_owned_portfolio(repo: PortfolioRepository, user_id: UUID, portfolio_id: UUID):
    portfolio = await repo.get_by_id(portfolio_id)
    if not portfolio:
        raise NotFoundError("Portfolio", str(portfolio_id))
    if portfolio.user_id != user_id:
        raise AuthorizationError("You do not own this portfolio")
    return portfolio


class ComputeRiskHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        holding_repo: HoldingRepository,
        snapshot_repo: RiskSnapshotRepository,
        limit_repo: RiskLimitRepository,
        session: AsyncSession,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._holding_repo = holding_repo
        self._snapshot_repo = snapshot_repo
        self._limit_repo = limit_repo
        self._session = session

    async def handle(self, command: ComputeRiskCommand) -> RiskSnapshotDTO:
        portfolio = await _get_owned_portfolio(
            self._portfolio_repo, command.user_id, command.portfolio_id
        )
        holdings = await self._holding_repo.list_by_portfolio(command.portfolio_id)
        await ReturnSeriesBuilder.refresh_holding_prices(self._session, holdings)

        port_rets, bench_rets, equity = await ReturnSeriesBuilder.portfolio_returns(
            self._session, holdings
        )
        metrics = RiskCalculator.compute(port_rets, bench_rets, equity_curve=equity)

        limits = await self._limit_repo.list_by_portfolio(command.portfolio_id)
        total_value = portfolio.cash_balance + sum(h.market_value for h in holdings)
        violations = LimitEnforcer.check(metrics, limits, holdings, total_value)
        metrics_blob = dict(metrics.metrics)
        if violations:
            metrics_blob["violations"] = violations

        snapshot = RiskSnapshot.create(
            command.portfolio_id,
            var_95=metrics.var_95,
            var_99=metrics.var_99,
            max_drawdown=metrics.max_drawdown,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            beta=metrics.beta,
            alpha=metrics.alpha,
            volatility=metrics.volatility,
            correlation_matrix=metrics.correlation_matrix,
            metrics=metrics_blob,
        )
        saved = await self._snapshot_repo.save(snapshot)

        return RiskSnapshotDTO.from_entity(saved, violations)


class ListRiskSnapshotsHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        snapshot_repo: RiskSnapshotRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._snapshot_repo = snapshot_repo

    async def handle(self, query: ListRiskSnapshotsQuery) -> tuple[list[RiskSnapshotDTO], int]:
        await _get_owned_portfolio(self._portfolio_repo, query.user_id, query.portfolio_id)
        items = await self._snapshot_repo.list_by_portfolio(
            query.portfolio_id, limit=query.limit, offset=query.offset
        )
        return [RiskSnapshotDTO.from_entity(s) for s in items], len(items)


class GetLatestRiskSnapshotHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        snapshot_repo: RiskSnapshotRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._snapshot_repo = snapshot_repo

    async def handle(self, query: GetLatestRiskSnapshotQuery) -> RiskSnapshotDTO:
        await _get_owned_portfolio(self._portfolio_repo, query.user_id, query.portfolio_id)
        snapshot = await self._snapshot_repo.get_latest(query.portfolio_id)
        if not snapshot:
            raise NotFoundError("RiskSnapshot", f"latest for {query.portfolio_id}")
        violations = snapshot.metrics.get("violations", [])
        return RiskSnapshotDTO.from_entity(
            snapshot, violations if isinstance(violations, list) else []
        )


class GetRiskLimitsHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        limit_repo: RiskLimitRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._limit_repo = limit_repo

    async def handle(self, query: GetRiskLimitsQuery) -> list[RiskLimitDTO]:
        await _get_owned_portfolio(self._portfolio_repo, query.user_id, query.portfolio_id)
        limits = await self._limit_repo.list_by_portfolio(query.portfolio_id)
        return [RiskLimitDTO.from_entity(item) for item in limits]


class UpdateRiskLimitsHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        limit_repo: RiskLimitRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._limit_repo = limit_repo

    async def handle(self, command: UpdateRiskLimitsCommand) -> list[RiskLimitDTO]:
        from alphaedge.modules.portfolio.domain.enums import RiskLimitType

        await _get_owned_portfolio(self._portfolio_repo, command.user_id, command.portfolio_id)
        saved: list[RiskLimitDTO] = []
        for raw in command.limits:
            limit_type = RiskLimitType(str(raw["limit_type"]))
            threshold = Decimal(str(raw["threshold"]))
            is_active = bool(raw.get("is_active", True))
            existing = await self._limit_repo.get_by_portfolio_and_type(
                command.portfolio_id, limit_type.value
            )
            if existing:
                existing.threshold = threshold
                existing.is_active = is_active
                entity = await self._limit_repo.upsert(existing)
            else:
                entity = await self._limit_repo.upsert(
                    RiskLimit.create(
                        command.portfolio_id, limit_type, threshold, is_active=is_active
                    )
                )
            saved.append(RiskLimitDTO.from_entity(entity))
        return saved
