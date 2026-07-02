from alphaedge.modules.optimization.application.commands import (
    GetBestTrialQuery,
    GetOptimizationRunQuery,
    ListOptimizationRunsQuery,
    ListOptimizationTrialsQuery,
    OptimizationRunDTO,
    OptimizationTrialDTO,
    SubmitOptimizationCommand,
)
from alphaedge.modules.optimization.domain.entities import OptimizationRun
from alphaedge.modules.optimization.domain.enums import (
    OptimizationMethod,
    OptimizationObjective,
)
from alphaedge.modules.optimization.domain.repositories import (
    OptimizationRunRepository,
    OptimizationTrialRepository,
)
from alphaedge.modules.strategy.domain.enums import VersionStatus
from alphaedge.modules.strategy.domain.repositories import (
    StrategyRepository,
    StrategyVersionRepository,
)
from alphaedge.shared.domain.exceptions import AuthorizationError, NotFoundError, ValidationError


class SubmitOptimizationHandler:
    def __init__(
        self,
        run_repo: OptimizationRunRepository,
        strategy_repo: StrategyRepository,
        version_repo: StrategyVersionRepository,
    ) -> None:
        self._run_repo = run_repo
        self._strategy_repo = strategy_repo
        self._version_repo = version_repo

    async def handle(self, command: SubmitOptimizationCommand) -> OptimizationRunDTO:
        version = await self._version_repo.get_by_id(command.strategy_version_id)
        if not version:
            raise NotFoundError("StrategyVersion", str(command.strategy_version_id))
        strategy = await self._strategy_repo.get_by_id(version.strategy_id)
        if not strategy or strategy.deleted_at is not None:
            raise NotFoundError("Strategy", str(version.strategy_id))
        if strategy.user_id != command.user_id:
            raise AuthorizationError("You do not own this strategy")
        if version.status != VersionStatus.VALIDATED:
            raise ValidationError("Strategy version must be validated before optimization")

        try:
            method = OptimizationMethod(command.method)
        except ValueError as exc:
            raise ValidationError(f"Invalid optimization method: {command.method}") from exc
        try:
            objective = OptimizationObjective(command.objective)
        except ValueError as exc:
            raise ValidationError(f"Invalid optimization objective: {command.objective}") from exc

        if method == OptimizationMethod.WALK_FORWARD and not command.walk_forward_config:
            raise ValidationError("walk_forward_config is required for walk_forward method")

        run = OptimizationRun.create(
            user_id=command.user_id,
            strategy_version_id=command.strategy_version_id,
            name=command.name,
            method=method,
            objective=objective,
            parameter_space=command.parameter_space,
            backtest_config=command.backtest_config,
            walk_forward_config=command.walk_forward_config,
        )
        saved = await self._run_repo.save(run)
        return OptimizationRunDTO.from_entity(saved)


class ListOptimizationRunsHandler:
    def __init__(self, run_repo: OptimizationRunRepository) -> None:
        self._run_repo = run_repo

    async def handle(
        self, query: ListOptimizationRunsQuery
    ) -> tuple[list[OptimizationRunDTO], int]:
        items = await self._run_repo.list_by_user(
            query.user_id, limit=query.limit, offset=query.offset
        )
        total = await self._run_repo.count_by_user(query.user_id)
        return [OptimizationRunDTO.from_entity(r) for r in items], total


class GetOptimizationRunHandler:
    def __init__(self, run_repo: OptimizationRunRepository) -> None:
        self._run_repo = run_repo

    async def handle(self, query: GetOptimizationRunQuery) -> OptimizationRunDTO:
        run = await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        return OptimizationRunDTO.from_entity(run)


class ListOptimizationTrialsHandler:
    def __init__(
        self,
        run_repo: OptimizationRunRepository,
        trial_repo: OptimizationTrialRepository,
    ) -> None:
        self._run_repo = run_repo
        self._trial_repo = trial_repo

    async def handle(self, query: ListOptimizationTrialsQuery) -> list[OptimizationTrialDTO]:
        await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        trials = await self._trial_repo.list_by_run_id(query.run_id)
        return [OptimizationTrialDTO.from_entity(t) for t in trials]


class GetBestTrialHandler:
    def __init__(
        self,
        run_repo: OptimizationRunRepository,
        trial_repo: OptimizationTrialRepository,
    ) -> None:
        self._run_repo = run_repo
        self._trial_repo = trial_repo

    async def handle(self, query: GetBestTrialQuery) -> OptimizationTrialDTO:
        run = await _get_owned_run(self._run_repo, query.user_id, query.run_id)
        if not run.best_trial_id:
            raise NotFoundError("OptimizationTrial", "best")
        trial = await self._trial_repo.get_by_id(run.best_trial_id)
        if not trial:
            raise NotFoundError("OptimizationTrial", str(run.best_trial_id))
        return OptimizationTrialDTO.from_entity(trial)


async def _get_owned_run(run_repo: OptimizationRunRepository, user_id, run_id) -> OptimizationRun:
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise NotFoundError("OptimizationRun", str(run_id))
    if run.user_id != user_id:
        raise AuthorizationError("You do not own this optimization run")
    return run
