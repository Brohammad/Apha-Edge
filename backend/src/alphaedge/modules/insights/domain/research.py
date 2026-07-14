"""External research provider port (Tavily, etc.)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchResult:
    query: str
    summary: str
    sources: list[dict[str, str]]


class ResearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, *, max_results: int = 5) -> ResearchResult:
        pass
