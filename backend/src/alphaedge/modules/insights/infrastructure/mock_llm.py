from typing import Any

from alphaedge.modules.insights.domain.enums import InsightType
from alphaedge.modules.insights.domain.llm import LLMProvider
from alphaedge.modules.insights.domain.prompts import LLMResponse
from alphaedge.modules.insights.infrastructure.mock_content import generate_mock_content


class MockLLMProvider(LLMProvider):
    """Deterministic provider for dev/CI — synthesizes structured Markdown from context."""

    async def complete(
        self,
        prompt: str,
        *,
        insight_type: InsightType | None = None,
        context: dict[str, Any] | None = None,
    ) -> LLMResponse:
        if insight_type and context:
            content = generate_mock_content(insight_type, context)
        else:
            content = (
                "# AI Insight Report\n\n"
                "> **Demo mode** — configure `LLM_PROVIDER=openai` and `OPENAI_API_KEY` "
                "for live model analysis.\n\n"
                "Insight context was not available; unable to synthesize a report."
            )

        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-llm-v1",
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(content.split()),
        )
