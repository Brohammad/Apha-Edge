import httpx

from alphaedge.config import settings
from alphaedge.modules.insights.domain.llm import LLMProvider
from alphaedge.modules.insights.domain.prompts import LLMResponse
from alphaedge.shared.domain.exceptions import ValidationError


class OpenAILLMProvider(LLMProvider):
    """OpenAI-compatible chat completions API."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini") -> None:
        self._api_key = api_key or settings.openai_api_key
        self._model = model
        if not self._api_key:
            raise ValidationError("OPENAI_API_KEY is required for OpenAI LLM provider")

    async def complete(self, prompt: str, **kwargs: object) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are AlphaEdge, a quantitative trading analyst.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            data = response.json()

        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResponse(
            content=str(choice),
            provider="openai",
            model=str(data.get("model", self._model)),
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
        )
