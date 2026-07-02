from abc import ABC, abstractmethod

from alphaedge.modules.insights.domain.prompts import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str) -> LLMResponse:
        pass
