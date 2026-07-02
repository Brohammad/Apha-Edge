from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from alphaedge.modules.backtesting.domain.entities import BacktestResult
from alphaedge.modules.optimization.domain.enums import OptimizationObjective
from alphaedge.modules.optimization.domain.services import (
    extract_objective,
    generate_grid_combinations,
    generate_walk_forward_windows,
    rank_trials,
)
from alphaedge.shared.domain.exceptions import ValidationError


def test_generate_grid_combinations():
    space = {"fast_period": [3, 5], "slow_period": [10, 20]}
    combos = generate_grid_combinations(space)
    assert len(combos) == 4
    assert {"fast_period": 3, "slow_period": 10} in combos
    assert {"fast_period": 5, "slow_period": 20} in combos


def test_generate_grid_combinations_rejects_empty():
    with pytest.raises(ValidationError):
        generate_grid_combinations({"fast_period": []})


def test_generate_walk_forward_windows():
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 6, 1, tzinfo=UTC)
    windows = generate_walk_forward_windows(
        start, end, {"train_days": 60, "test_days": 20, "step_days": 20}
    )
    assert len(windows) >= 1
    assert windows[0].train_start == start
    assert windows[0].test_end <= end


def test_extract_objective_sharpe():
    result = BacktestResult.create(
        backtest_run_id=uuid4(),
        total_return=Decimal("0.15"),
        max_drawdown=Decimal("0.05"),
        total_trades=10,
        equity_curve=[],
        metrics={},
        sharpe_ratio=Decimal("1.25"),
    )
    assert extract_objective(result, OptimizationObjective.SHARPE_RATIO) == Decimal("1.25")


def test_extract_objective_max_drawdown_negated():
    result = BacktestResult.create(
        backtest_run_id=uuid4(),
        total_return=Decimal("0.15"),
        max_drawdown=Decimal("0.10"),
        total_trades=10,
        equity_curve=[],
        metrics={},
    )
    assert extract_objective(result, OptimizationObjective.MAX_DRAWDOWN) == Decimal("-0.10")


def test_rank_trials_orders_by_objective_desc():
    items = [("a", Decimal("1.0")), ("b", Decimal("2.5")), ("c", Decimal("1.5"))]
    ranked = rank_trials(items)
    assert ranked[0][0] == "b"
    assert ranked[0][2] == 1
    assert ranked[1][0] == "c"
    assert ranked[2][0] == "a"
