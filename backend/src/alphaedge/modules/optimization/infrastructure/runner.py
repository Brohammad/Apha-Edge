import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from alphaedge.modules.backtesting.domain.config import BacktestConfig
from alphaedge.modules.backtesting.domain.entities import BacktestRun
from alphaedge.modules.backtesting.domain.enums import BacktestStatus
from alphaedge.modules.backtesting.infrastructure.models import (
    SQLAlchemyBacktestResultRepository,
    SQLAlchemyBacktestRunRepository,
)
from alphaedge.modules.backtesting.infrastructure.runner import execute_backtest
from alphaedge.modules.optimization.domain.entities import OptimizationRun, OptimizationTrial
from alphaedge.modules.optimization.domain.enums import (
    OptimizationMethod,
    OptimizationStatus,
    TrialStatus,
)
from alphaedge.modules.optimization.domain.services import (
    extract_objective,
    generate_grid_combinations,
    generate_walk_forward_windows,
    merge_backtest_config,
    rank_trials,
)
from alphaedge.modules.optimization.infrastructure.models import (
    SQLAlchemyOptimizationRunRepository,
    SQLAlchemyOptimizationTrialRepository,
)
from alphaedge.shared.infrastructure.database import async_session_factory


async def execute_optimization(run_id: UUID) -> None:
    async with async_session_factory() as session:
        run_repo = SQLAlchemyOptimizationRunRepository(session)
        trial_repo = SQLAlchemyOptimizationTrialRepository(session)
        backtest_run_repo = SQLAlchemyBacktestRunRepository(session)

        run = await run_repo.get_by_id(run_id)
        if not run or run.status == OptimizationStatus.CANCELLED:
            return

        run.status = OptimizationStatus.RUNNING
        run.started_at = datetime.now(UTC)
        await run_repo.update(run)
        await session.commit()

        try:
            if run.method == OptimizationMethod.WALK_FORWARD:
                await _execute_walk_forward(session, run, run_repo, trial_repo, backtest_run_repo)
            else:
                await _execute_grid_search(session, run, run_repo, trial_repo, backtest_run_repo)
            await session.commit()
        except Exception as exc:
            await session.rollback()
            run = await run_repo.get_by_id(run_id)
            if run:
                run.status = OptimizationStatus.FAILED
                run.error_message = str(exc)[:2000]
                run.completed_at = datetime.now(UTC)
                await run_repo.update(run)
                await session.commit()
            raise


async def execute_optimization_trial(run_id: UUID, trial_id: UUID) -> None:
    """Run a single trial backtest (used by Celery parallel workers)."""
    async with async_session_factory() as session:
        run_repo = SQLAlchemyOptimizationRunRepository(session)
        trial_repo = SQLAlchemyOptimizationTrialRepository(session)
        backtest_run_repo = SQLAlchemyBacktestRunRepository(session)
        result_repo = SQLAlchemyBacktestResultRepository(session)

        run = await run_repo.get_by_id(run_id)
        trial = await trial_repo.get_by_id(trial_id)
        if not run or not trial or run.status == OptimizationStatus.CANCELLED:
            return

        await _run_trial_backtest(
            session,
            run,
            trial,
            trial_repo,
            backtest_run_repo,
            result_repo,
        )
        run.completed_trials += 1
        await run_repo.update(run)
        await session.commit()

        if run.completed_trials >= run.total_trials:
            await _finalize_run(run_id)


async def _execute_grid_search(
    session,
    run: OptimizationRun,
    run_repo: SQLAlchemyOptimizationRunRepository,
    trial_repo: SQLAlchemyOptimizationTrialRepository,
    backtest_run_repo: SQLAlchemyBacktestRunRepository,
) -> None:
    combos = generate_grid_combinations(run.parameter_space)
    trials = [OptimizationTrial.create(run.id, params) for params in combos]
    await trial_repo.save_many(trials)

    run.total_trials = len(trials)
    run.completed_trials = 0
    await run_repo.update(run)
    await session.commit()

    result_repo = SQLAlchemyBacktestResultRepository(session)
    for trial in trials:
        await _run_trial_backtest(session, run, trial, trial_repo, backtest_run_repo, result_repo)
        run.completed_trials += 1
        await run_repo.update(run)
        await session.commit()

    await _finalize_run(run.id)


async def _execute_walk_forward(
    session,
    run: OptimizationRun,
    run_repo: SQLAlchemyOptimizationRunRepository,
    trial_repo: SQLAlchemyOptimizationTrialRepository,
    backtest_run_repo: SQLAlchemyBacktestRunRepository,
) -> None:
    if not run.walk_forward_config:
        raise ValueError("walk_forward_config is required for walk_forward method")

    base_config = BacktestConfig.from_dict(run.backtest_config)
    windows = generate_walk_forward_windows(
        base_config.start_date, base_config.end_date, run.walk_forward_config
    )
    combos = generate_grid_combinations(run.parameter_space)
    result_repo = SQLAlchemyBacktestResultRepository(session)

    oos_trials: list[OptimizationTrial] = []
    run.total_trials = len(windows)
    run.completed_trials = 0
    await run_repo.update(run)
    await session.commit()

    for window in windows:
        in_sample_results: list[tuple[OptimizationTrial, Decimal | None]] = []
        for params in combos:
            trial = OptimizationTrial.create(run.id, params, window_index=window.index)
            await trial_repo.save(trial)
            is_config = merge_backtest_config(
                run.backtest_config,
                start_date=window.train_start,
                end_date=window.train_end,
                strategy_parameters=params,
            )
            is_value = await _run_backtest_for_trial(
                session,
                run,
                trial,
                is_config,
                backtest_run_repo,
                result_repo,
                trial_repo,
            )
            in_sample_results.append((trial, is_value))

        ranked = rank_trials(in_sample_results)
        best_trial, best_is_value, _ = ranked[0]

        oos_trial = OptimizationTrial.create(
            run.id,
            best_trial.parameters,
            window_index=window.index,
        )
        await trial_repo.save(oos_trial)
        oos_config = merge_backtest_config(
            run.backtest_config,
            start_date=window.test_start,
            end_date=window.test_end,
            strategy_parameters=best_trial.parameters,
        )
        oos_value = await _run_backtest_for_trial(
            session,
            run,
            oos_trial,
            oos_config,
            backtest_run_repo,
            result_repo,
            trial_repo,
            in_sample_objective=best_is_value,
        )
        oos_trial.in_sample_objective = best_is_value
        oos_trial.objective_value = oos_value
        oos_trial.status = TrialStatus.COMPLETED
        await trial_repo.update(oos_trial)
        oos_trials.append(oos_trial)

        run.completed_trials += 1
        await run_repo.update(run)
        await session.commit()

    ranked_oos = rank_trials([(t, t.objective_value) for t in oos_trials])
    for trial, _, rank in ranked_oos:
        trial.rank = rank
    await trial_repo.update_many([t for t, _, _ in ranked_oos])

    if ranked_oos:
        best = ranked_oos[0][0]
        run.best_trial_id = best.id
    run.status = OptimizationStatus.COMPLETED
    run.completed_at = datetime.now(UTC)
    await run_repo.update(run)


async def _run_trial_backtest(
    session,
    run: OptimizationRun,
    trial: OptimizationTrial,
    trial_repo: SQLAlchemyOptimizationTrialRepository,
    backtest_run_repo: SQLAlchemyBacktestRunRepository,
    result_repo: SQLAlchemyBacktestResultRepository,
) -> None:
    config = merge_backtest_config(run.backtest_config, strategy_parameters=trial.parameters)
    objective_value = await _run_backtest_for_trial(
        session,
        run,
        trial,
        config,
        backtest_run_repo,
        result_repo,
        trial_repo,
    )
    trial.objective_value = objective_value
    trial.status = TrialStatus.COMPLETED
    await trial_repo.update(trial)


async def _run_backtest_for_trial(
    session,
    run: OptimizationRun,
    trial: OptimizationTrial,
    config: dict[str, object],
    backtest_run_repo: SQLAlchemyBacktestRunRepository,
    result_repo: SQLAlchemyBacktestResultRepository,
    trial_repo: SQLAlchemyOptimizationTrialRepository,
    in_sample_objective: Decimal | None = None,
) -> Decimal | None:
    trial.status = TrialStatus.RUNNING
    await trial_repo.update(trial)

    bt_run = BacktestRun.create(
        user_id=run.user_id,
        strategy_version_id=run.strategy_version_id,
        name=f"{run.name} trial {trial.id.hex[:8]}",
        config=config,
    )
    bt_run.status = BacktestStatus.QUEUED
    saved_bt = await backtest_run_repo.save(bt_run)
    trial.backtest_run_id = saved_bt.id
    await trial_repo.update(trial)
    await session.commit()

    await execute_backtest(saved_bt.id)

    result = await result_repo.get_by_run_id(saved_bt.id)
    if not result:
        trial.status = TrialStatus.FAILED
        await trial_repo.update(trial)
        return None

    objective_value = extract_objective(result, run.objective)
    if in_sample_objective is not None:
        trial.in_sample_objective = in_sample_objective
    trial.objective_value = objective_value
    trial.status = TrialStatus.COMPLETED
    await trial_repo.update(trial)
    return objective_value


async def _finalize_run(run_id: UUID) -> None:
    async with async_session_factory() as session:
        run_repo = SQLAlchemyOptimizationRunRepository(session)
        trial_repo = SQLAlchemyOptimizationTrialRepository(session)

        run = await run_repo.get_by_id(run_id)
        if not run:
            return

        trials = await trial_repo.list_by_run_id(run_id)
        completed = [t for t in trials if t.status == TrialStatus.COMPLETED]
        ranked = rank_trials([(t, t.objective_value) for t in completed])
        for trial, _, rank in ranked:
            trial.rank = rank
        await trial_repo.update_many([t for t, _, _ in ranked])

        if ranked:
            run.best_trial_id = ranked[0][0].id
        run.status = OptimizationStatus.COMPLETED
        run.completed_at = datetime.now(UTC)
        await run_repo.update(run)
        await session.commit()


def run_optimization_sync(run_id: str) -> None:
    asyncio.run(execute_optimization(UUID(run_id)))


def run_optimization_trial_sync(run_id: str, trial_id: str) -> None:
    asyncio.run(execute_optimization_trial(UUID(run_id), UUID(trial_id)))
