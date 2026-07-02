from abc import ABC, abstractmethod
from datetime import datetime

from alphaedge.modules.market_data.domain.enums import Timeframe
from alphaedge.modules.market_data.domain.services import RawBar


class MarketDataProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def fetch_bars(
        self,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[RawBar]: ...
