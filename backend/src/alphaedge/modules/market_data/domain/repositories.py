from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from alphaedge.modules.market_data.domain.entities import Bar, IngestionJob, Instrument
from alphaedge.modules.market_data.domain.enums import Timeframe


class InstrumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, instrument_id: UUID) -> Instrument | None: ...

    @abstractmethod
    async def get_by_symbol(self, symbol: str) -> Instrument | None: ...

    @abstractmethod
    async def list_all(
        self, *, active_only: bool = True, limit: int = 100, offset: int = 0
    ) -> list[Instrument]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 20) -> list[Instrument]: ...

    @abstractmethod
    async def save(self, instrument: Instrument) -> Instrument: ...

    @abstractmethod
    async def count(self, *, active_only: bool = True) -> int: ...


class BarRepository(ABC):
    @abstractmethod
    async def upsert_many(self, bars: list[Bar]) -> int: ...

    @abstractmethod
    async def get_bars(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Bar]: ...

    @abstractmethod
    async def get_latest(self, instrument_id: UUID, timeframe: Timeframe) -> Bar | None: ...

    @abstractmethod
    async def count(
        self,
        instrument_id: UUID,
        timeframe: Timeframe,
        start: datetime | None,
        end: datetime | None,
    ) -> int: ...


class IngestionJobRepository(ABC):
    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> IngestionJob | None: ...

    @abstractmethod
    async def save(self, job: IngestionJob) -> IngestionJob: ...

    @abstractmethod
    async def update(self, job: IngestionJob) -> IngestionJob: ...
