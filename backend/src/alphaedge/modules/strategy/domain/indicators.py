from abc import ABC, abstractmethod
from collections import deque
from decimal import Decimal

from alphaedge.modules.market_data.domain.entities import Bar
from alphaedge.modules.strategy.domain.value_objects import Signal, StrategyContext, Tick


class StrategyBase(ABC):
    """Base class for Python-authored trading strategies."""

    def on_init(self, context: StrategyContext) -> None:  # noqa: B027
        """Called once before the strategy receives market data."""

    @abstractmethod
    def on_bar(self, bar: Bar, context: StrategyContext) -> Signal | None:
        """Process an OHLCV bar and optionally emit a signal."""

    def on_tick(self, tick: Tick, context: StrategyContext) -> Signal | None:
        """Process a tick update; override for tick-driven strategies."""
        return None

    def on_stop(self, context: StrategyContext) -> None:  # noqa: B027
        """Called when the strategy run ends."""


class Indicator(ABC):
    """Stateful indicator that updates incrementally."""

    @abstractmethod
    def update(self, value: Decimal) -> Decimal | None:
        """Feed a new value; return indicator output when ready."""

    @abstractmethod
    def reset(self) -> None:
        """Clear internal state."""

    @property
    @abstractmethod
    def ready(self) -> bool:
        """True once the indicator has enough data to produce values."""


class SMA(Indicator):
    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("SMA period must be >= 1")
        self._period = period
        self._window: deque[Decimal] = deque(maxlen=period)

    @property
    def ready(self) -> bool:
        return len(self._window) == self._period

    def reset(self) -> None:
        self._window.clear()

    def update(self, value: Decimal) -> Decimal | None:
        self._window.append(value)
        if not self.ready:
            return None
        return sum(self._window, Decimal("0")) / self._period


class EMA(Indicator):
    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("EMA period must be >= 1")
        self._period = period
        self._multiplier = Decimal("2") / (Decimal(period) + Decimal("1"))
        self._value: Decimal | None = None
        self._count = 0

    @property
    def ready(self) -> bool:
        return self._count >= self._period

    def reset(self) -> None:
        self._value = None
        self._count = 0

    def update(self, value: Decimal) -> Decimal | None:
        self._count += 1
        if self._value is None:
            self._value = value
        else:
            self._value = (value - self._value) * self._multiplier + self._value
        if not self.ready:
            return None
        return self._value


class RSI(Indicator):
    def __init__(self, period: int = 14) -> None:
        if period < 2:
            raise ValueError("RSI period must be >= 2")
        self._period = period
        self._prev: Decimal | None = None
        self._gains: deque[Decimal] = deque(maxlen=period)
        self._losses: deque[Decimal] = deque(maxlen=period)

    @property
    def ready(self) -> bool:
        return len(self._gains) == self._period

    def reset(self) -> None:
        self._prev = None
        self._gains.clear()
        self._losses.clear()

    def update(self, value: Decimal) -> Decimal | None:
        if self._prev is not None:
            change = value - self._prev
            self._gains.append(max(change, Decimal("0")))
            self._losses.append(max(-change, Decimal("0")))
        self._prev = value
        if not self.ready:
            return None
        avg_gain = sum(self._gains, Decimal("0")) / self._period
        avg_loss = sum(self._losses, Decimal("0")) / self._period
        if avg_loss == 0:
            return Decimal("100")
        rs = avg_gain / avg_loss
        return Decimal("100") - (Decimal("100") / (Decimal("1") + rs))


class MACD(Indicator):
    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> None:
        self._macd_line = EMA(fast_period)
        self._slow_ema = EMA(slow_period)
        self._signal_line = EMA(signal_period)
        self._last_macd: Decimal | None = None

    @property
    def ready(self) -> bool:
        return self._signal_line.ready

    def reset(self) -> None:
        self._macd_line.reset()
        self._slow_ema.reset()
        self._signal_line.reset()
        self._last_macd = None

    def update(self, value: Decimal) -> Decimal | None:
        fast = self._macd_line.update(value)
        slow = self._slow_ema.update(value)
        if fast is None or slow is None:
            return None
        macd = fast - slow
        signal = self._signal_line.update(macd)
        self._last_macd = macd
        return signal

    @property
    def macd_line(self) -> Decimal | None:
        return self._last_macd


class BollingerBands(Indicator):
    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        self._period = period
        self._std_dev = Decimal(str(std_dev))
        self._sma = SMA(period)
        self._window: deque[Decimal] = deque(maxlen=period)
        self._middle: Decimal | None = None
        self._upper: Decimal | None = None
        self._lower: Decimal | None = None

    @property
    def ready(self) -> bool:
        return self._sma.ready

    @property
    def middle(self) -> Decimal | None:
        return self._middle

    @property
    def upper(self) -> Decimal | None:
        return self._upper

    @property
    def lower(self) -> Decimal | None:
        return self._lower

    def reset(self) -> None:
        self._sma.reset()
        self._window.clear()
        self._middle = None
        self._upper = None
        self._lower = None

    def update(self, value: Decimal) -> Decimal | None:
        self._window.append(value)
        middle = self._sma.update(value)
        if middle is None or len(self._window) < self._period:
            return None
        variance = sum((x - middle) ** 2 for x in self._window) / self._period
        std = variance.sqrt() if variance >= 0 else Decimal("0")
        self._middle = middle
        self._upper = middle + self._std_dev * std
        self._lower = middle - self._std_dev * std
        return middle


INDICATOR_REGISTRY: dict[str, type[Indicator]] = {
    "sma": SMA,
    "ema": EMA,
    "rsi": RSI,
    "macd": MACD,
    "bollinger": BollingerBands,
}


def create_indicator(name: str, params: dict[str, object]) -> Indicator:
    cls = INDICATOR_REGISTRY.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown indicator: {name}")
    if name.lower() == "macd":
        return cls(
            fast_period=int(params.get("fast_period", 12)),
            slow_period=int(params.get("slow_period", 26)),
            signal_period=int(params.get("signal_period", 9)),
        )
    if name.lower() == "bollinger":
        return cls(
            period=int(params.get("period", 20)),
            std_dev=float(params.get("std_dev", 2.0)),
        )
    return cls(period=int(params.get("period", 20)))


def crossover(prev_a: Decimal | None, prev_b: Decimal | None, a: Decimal, b: Decimal) -> bool:
    if prev_a is None or prev_b is None:
        return False
    return prev_a <= prev_b and a > b


def crossunder(prev_a: Decimal | None, prev_b: Decimal | None, a: Decimal, b: Decimal) -> bool:
    if prev_a is None or prev_b is None:
        return False
    return prev_a >= prev_b and a < b
