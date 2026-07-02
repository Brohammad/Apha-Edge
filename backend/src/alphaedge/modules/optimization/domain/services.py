import itertools
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from alphaedge.modules.backtesting.domain.entities import BacktestResult
from alphaedge.modules.optimization.domain.enums import OptimizationObjective
from alphaedge.shared.domain.exceptions import ValidationError


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime


def generate_grid_combinations(parameter_space: dict[str, object]) -> list[dict[str, object]]:
    """Cartesian product of discrete parameter values."""
    keys: list[str] = []
    value_lists: list[list[object]] = []
    for key, values in parameter_space.items():
        if not isinstance(values, list) or len(values) == 0:
            raise ValidationError(f"parameter_space['{key}'] must be a non-empty list")
        keys.append(key)
        value_lists.append(values)
    combos: list[dict[str, object]] = []
    for product in itertools.product(*value_lists):
        combos.append(dict(zip(keys, product, strict=True)))
    return combos


def generate_walk_forward_windows(
    start_date: datetime,
    end_date: datetime,
    config: dict[str, object],
) -> list[WalkForwardWindow]:
    train_days = int(config.get("train_days", 60))
    test_days = int(config.get("test_days", 20))
    step_days = int(config.get("step_days", test_days))
    if train_days <= 0 or test_days <= 0 or step_days <= 0:
        raise ValidationError("train_days, test_days, and step_days must be positive")

    windows: list[WalkForwardWindow] = []
    cursor = start_date
    index = 0
    while True:
        train_start = cursor
        train_end = train_start + timedelta(days=train_days)
        test_start = train_end
        test_end = test_start + timedelta(days=test_days)
        if test_end > end_date:
            break
        windows.append(
            WalkForwardWindow(
                index=index,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
        cursor += timedelta(days=step_days)
        index += 1

    if not windows:
        raise ValidationError("walk_forward config produces no windows for the date range")
    return windows


def extract_objective(result: BacktestResult, objective: OptimizationObjective) -> Decimal | None:
    if objective == OptimizationObjective.SHARPE_RATIO:
        return result.sharpe_ratio
    if objective == OptimizationObjective.TOTAL_RETURN:
        return result.total_return
    if objective == OptimizationObjective.SORTINO_RATIO:
        return result.sortino_ratio
    if objective == OptimizationObjective.MAX_DRAWDOWN:
        # Lower drawdown is better; negate so ranking logic stays "higher is better"
        return -result.max_drawdown
    return None


def rank_trials(
    trials: list[tuple[object, Decimal | None]],
) -> list[tuple[object, Decimal | None, int]]:
    """Rank items by objective value descending; None values rank last."""
    sorted_items = sorted(
        trials,
        key=lambda item: (item[1] is not None, item[1] or Decimal("-999999")),
        reverse=True,
    )
    ranked: list[tuple[object, Decimal | None, int]] = []
    for rank, (item, value) in enumerate(sorted_items, start=1):
        ranked.append((item, value, rank))
    return ranked


def merge_backtest_config(
    base: dict[str, object],
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    strategy_parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    merged = dict(base)
    if start_date is not None:
        merged["start_date"] = start_date.isoformat()
    if end_date is not None:
        merged["end_date"] = end_date.isoformat()
    if strategy_parameters is not None:
        merged["strategy_parameters"] = strategy_parameters
    return merged
