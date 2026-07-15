"""Strategy sandbox timeout helpers."""

import time

import pytest

from alphaedge.modules.backtesting.domain.sandbox import (
    StrategyTimeoutError,
    run_with_timeout,
)


def test_run_with_timeout_completes() -> None:
    assert run_with_timeout(lambda: 42, seconds=2.0, label="ok") == 42


def test_run_with_timeout_raises_on_hang() -> None:
    def hang() -> None:
        time.sleep(5)

    with pytest.raises(StrategyTimeoutError):
        run_with_timeout(hang, seconds=0.2, label="hang")
