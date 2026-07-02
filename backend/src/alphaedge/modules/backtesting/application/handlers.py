from alphaedge.modules.backtesting.application.commands import (
    BacktestResultDTO,
    BacktestRunDTO,
    BacktestTradeDTO,
    DeleteBacktestRunCommand,
    GetBacktestResultQuery,
    GetBacktestRunQuery,
    GetBacktestTradesQuery,
    GetEquityCurveQuery,
    ListBacktestRunsQuery,
    SubmitBacktestCommand,
)
from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.entities import BacktestRun
from alphaedge.modules.backtesting.domain.enums import BacktestStatus
from alphaedge.modules.backtesting.domain.repositories import (
    BacktestResultRepository,
    BacktestRunRepository,
    BacktestTradeRepository,
)
from alphaedge.modules.strategy.domain.enums import VersionStatus
from alphaedge.modules.strategy.domain.repositories import (
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


class SubmitBacktestHandler:
    def __init__(
        self,
        run_repo: BacktestRunRepository,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._run_repo = run_repo
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, command: SubmitBacktestCommand) -> BacktestRunDTO:
        version = await self._version_repo.get_by_id(command.strategy_version_id)
        if not version:
            raise NotFoundError("StrategyVersion", str(command.strategy_version_id))
        strategy = await self._strategy_repo.get_by_id(version.strategy_id)
        if not strategy or strategy.deleted_at is not None:
            raise NotFoundError("Strategy", str(version.strategy_id))
        if strategy.user_id != command.user_id:
            raise AuthorizationError("You do not own this strategy")
        if version.status != VersionStatus.VALIDATED:
            raise ValidationError("Strategy version must be validated before backtesting")

        config = BacktestConfig.from_dict(command.config)
        run = BacktestRun.create(
            user_id=command.user_id,
            strategy_version_id=command.strategy_version_id,
            name=command.name,
            config=config.to_dict(),
        )
        saved = await self._run_repo.save(run)
        return BacktestRunDTO.from_entity(saved)


class ListBacktestRunsHandler:
    def __init__(self, run_repo: BacktestRunRepository) -> None:
        self._run_repo = run_repo

    async def handle(self, query: ListBacktestRunsQuery) -> tuple[list[BacktestRunDTO], int]:
        items = await self._run_repo.list_by_user(
            query.user_id, limit=query.limit, offset=query.offset
        )
        total = await self._run_repo.count_by_user(query.user_id)
        return [BacktestRunDTO.from_entity(r) for r in items], total


class GetBacktestRunHandler:
    def __init__(self, run_repo: BacktestRunRepository) -> None:
        self._run_repo = run_repo

    async def handle(self, query: GetBacktestRunQuery) -> BacktestRunDTO:
        run = await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        return BacktestRunDTO.from_entity(run)


class GetBacktestResultHandler:
    def __init__(
        self,
        run_repo: BacktestRunRepository,
        result_repo: BacktestResultRepository,
    ) -> None:
        self._run_repo = run_repo
        self._result_repo = result_repo

    async def handle(self, query: GetBacktestResultQuery) -> BacktestResultDTO:
        await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        result = await self._result_repo.get_by_run_id(query.run_id)
        if not result:
            raise NotFoundError("BacktestResult", str(query.run_id))
        return BacktestResultDTO.from_entity(result)


class GetBacktestTradesHandler:
    def __init__(
        self,
        run_repo: BacktestRunRepository,
        trade_repo: BacktestTradeRepository,
    ) -> None:
        self._run_repo = run_repo
        self._trade_repo = trade_repo

    async def handle(self, query: GetBacktestTradesQuery) -> list[BacktestTradeDTO]:
        await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        trades = await self._trade_repo.list_by_run_id(query.run_id)
        return [BacktestTradeDTO.from_entity(t) for t in trades]


class GetEquityCurveHandler:
    def __init__(
        self,
        run_repo: BacktestRunRepository,
        result_repo: BacktestResultRepository,
    ) -> None:
        self._run_repo = run_repo
        self._result_repo = result_repo

    async def handle(self, query: GetEquityCurveQuery) -> list[dict[str, object]]:
        await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        result = await self._result_repo.get_by_run_id(query.run_id)
        if not result:
            raise NotFoundError("BacktestResult", str(query.run_id))
        return result.equity_curve


class DeleteBacktestRunHandler:
    def __init__(self, run_repo: BacktestRunRepository) -> None:
        self._run_repo = run_repo

    async def handle(self, command: DeleteBacktestRunCommand) -> None:
        run = await _get_owned_run(self._run_repo, command.user_id, command.run_id)
        if run.status in (BacktestStatus.RUNNING, BacktestStatus.QUEUED):
            run.status = BacktestStatus.CANCELLED
            await self._run_repo.update(run)


async def _get_owned_run(
    run_repo: BacktestRunRepository, user_id, run_id
) -> BacktestRun:
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise NotFoundError("BacktestRun", str(run_id))
    if run.user_id != user_id:
        raise AuthorizationError("You do not own this backtest run")
    return run
