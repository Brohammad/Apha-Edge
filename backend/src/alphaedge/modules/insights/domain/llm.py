from abc import ABC, abstractmethod
from typing import Any

from alphaedge.modules.insights.domain.enums import InsightType
from alphaedge.modules.insights.domain.prompts import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        insight_type: InsightType | None = None,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        pass
