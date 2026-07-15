"""Strategy runner factory tests."""

from alphaedge.modules.backtesting.domain.strategy_runner import (
    InProcessStrategyRunner,
    create_strategy_runner,
)

_SOURCE = '''
from alphaedge.modules.strategy.domain import StrategyBase, Signal, SignalAction

class S(StrategyBase):
    def on_bar(self, bar, context):
        return None
'''


def test_create_inprocess_runner_by_default() -> None:
    runner = create_strategy_runner(_SOURCE, {}, mode="inprocess")
    assert isinstance(runner, InProcessStrategyRunner)
    runner.on_stop()
