from alphaedge.modules.insights.domain.llm import LLMProvider
from alphaedge.modules.insights.domain.prompts import LLMResponse


class MockLLMProvider(LLMProvider):
    """Deterministic provider for dev/CI — structures the prompt into Markdown."""

    async def complete(self, prompt: str) -> LLMResponse:
        sections = prompt.strip().split("\n\n", 1)
        header = sections[0] if sections else "Analysis"
        body = sections[1] if len(sections) > 1 else prompt
        content = f"# AI Insight Report\n\n## Summary\n\n{header}\n\n## Analysis\n\n{body}\n"
        return LLMResponse(
            content=content,
            model="mock-llm-v1",
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(content.split()),
        )
