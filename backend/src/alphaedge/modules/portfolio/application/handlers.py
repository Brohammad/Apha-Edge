from uuid import UUID

from alphaedge.modules.backtesting.domain.repositories import BacktestTradeRepository
from alphaedge.modules.market_data.domain.repositories import InstrumentRepository
from alphaedge.modules.portfolio.application.commands import (
    CreatePortfolioCommand,
    GenerateRebalanceCommand,
    GetHoldingsQuery,
    GetPerformanceQuery,
    GetPortfolioQuery,
    GetRebalancePlanQuery,
    HoldingDTO,
    ListPortfoliosQuery,
    PortfolioDTO,
    RebalancePlanDTO,
    SyncFromBacktestCommand,
)
from alphaedge.modules.portfolio.domain.entities import RebalancePlan
from alphaedge.modules.portfolio.domain.repositories import (
    HoldingRepository,
    PortfolioRepository,
    RebalancePlanRepository,
)
from alphaedge.modules.portfolio.domain.services import (
    HoldingsSync,
    PerformanceCalculator,
    Rebalancer,
)
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError


async def _get_owned_portfolio(repo: PortfolioRepository, user_id: UUID, portfolio_id: UUID):
    portfolio = await repo.get_by_id(portfolio_id)
    if not portfolio:
        raise NotFoundError("Portfolio", str(portfolio_id))
    if portfolio.user_id != user_id:
        raise AuthorizationError("You do not own this portfolio")
    return portfolio


class CreatePortfolioHandler:
    def __init__(self, repo: PortfolioRepository) -> None:
        self._repo = repo

    async def handle(self, command: CreatePortfolioCommand) -> PortfolioDTO:
        from alphaedge.modules.portfolio.domain.entities import Portfolio

        portfolio = Portfolio.create(
            command.user_id,
            command.name,
            command.initial_capital,
            base_currency=command.base_currency,
            is_paper=command.is_paper,
        )
        saved = await self._repo.save(portfolio)
        return PortfolioDTO.from_entity(saved)


class ListPortfoliosHandler:
    def __init__(self, repo: PortfolioRepository) -> None:
        self._repo = repo

    async def handle(self, query: ListPortfoliosQuery) -> tuple[list[PortfolioDTO], int]:
        items = await self._repo.list_by_user(query.user_id, limit=query.limit, offset=query.offset)
        total = await self._repo.count_by_user(query.user_id)
        return [PortfolioDTO.from_entity(p) for p in items], total


class GetPortfolioHandler:
    def __init__(self, repo: PortfolioRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetPortfolioQuery) -> PortfolioDTO:
        portfolio = await _get_owned_portfolio(self._repo, query.user_id, query.portfolio_id)
        return PortfolioDTO.from_entity(portfolio)


class GetHoldingsHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        holding_repo: HoldingRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._holding_repo = holding_repo

    async def handle(self, query: GetHoldingsQuery) -> list[HoldingDTO]:
        await _get_owned_portfolio(self._portfolio_repo, query.user_id, query.portfolio_id)
        holdings = await self._holding_repo.list_by_portfolio(query.portfolio_id)
        return [HoldingDTO.from_entity(h) for h in holdings]


class GetPerformanceHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        holding_repo: HoldingRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._holding_repo = holding_repo

    async def handle(self, query: GetPerformanceQuery) -> dict[str, object]:
        portfolio = await _get_owned_portfolio(
            self._portfolio_repo, query.user_id, query.portfolio_id
        )
        holdings = await self._holding_repo.list_by_portfolio(query.portfolio_id)
        return PerformanceCalculator.summarize(portfolio, holdings)


class GenerateRebalanceHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        holding_repo: HoldingRepository,
        plan_repo: RebalancePlanRepository,
        instrument_repo: InstrumentRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._holding_repo = holding_repo
        self._plan_repo = plan_repo
        self._instrument_repo = instrument_repo

    async def handle(self, command: GenerateRebalanceCommand) -> RebalancePlanDTO:
        portfolio = await _get_owned_portfolio(
            self._portfolio_repo, command.user_id, command.portfolio_id
        )
        holdings = await self._holding_repo.list_by_portfolio(command.portfolio_id)
        symbol_map: dict[UUID, str] = {}
        for h in holdings:
            inst = await self._instrument_repo.get_by_id(h.instrument_id)
            if inst:
                symbol_map[h.instrument_id] = inst.symbol
        for symbol in command.target_allocation:
            inst = await self._instrument_repo.get_by_symbol(symbol)
            if inst:
                symbol_map[inst.id] = inst.symbol

        trades = Rebalancer.generate(
            portfolio,
            holdings,
            command.target_allocation,
            symbol_by_instrument=symbol_map,
        )
        plan = RebalancePlan.create(command.portfolio_id, command.target_allocation, trades)
        saved = await self._plan_repo.save(plan)
        return RebalancePlanDTO.from_entity(saved)


class GetRebalancePlanHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        plan_repo: RebalancePlanRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._plan_repo = plan_repo

    async def handle(self, query: GetRebalancePlanQuery) -> RebalancePlanDTO:
        await _get_owned_portfolio(self._portfolio_repo, query.user_id, query.portfolio_id)
        plan = await self._plan_repo.get_by_id(query.plan_id)
        if not plan or plan.portfolio_id != query.portfolio_id:
            raise NotFoundError("RebalancePlan", str(query.plan_id))
        return RebalancePlanDTO.from_entity(plan)


class SyncFromBacktestHandler:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        holding_repo: HoldingRepository,
        trade_repo: BacktestTradeRepository,
        backtest_run_repo,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._holding_repo = holding_repo
        self._trade_repo = trade_repo
        self._run_repo = backtest_run_repo

    async def handle(self, command: SyncFromBacktestCommand) -> list[HoldingDTO]:
        portfolio = await _get_owned_portfolio(
            self._portfolio_repo, command.user_id, command.portfolio_id
        )
        run = await self._run_repo.get_by_id(command.backtest_run_id)
        if not run or run.user_id != command.user_id:
            raise NotFoundError("BacktestRun", str(command.backtest_run_id))
        trades = await self._trade_repo.list_by_run_id(command.backtest_run_id)
        updated = await HoldingsSync.apply_backtest_trades(portfolio, self._holding_repo, trades)
        return [HoldingDTO.from_entity(h) for h in updated]
