import pytest

from alphaedge.modules.insights.domain.enums import InsightType
from alphaedge.modules.insights.domain.prompts import get_prompt, render_prompt
from alphaedge.modules.insights.infrastructure.mock_llm import MockLLMProvider


def test_get_prompt_all_types():
    for insight_type in InsightType:
        prompt = get_prompt(insight_type)
        assert len(prompt) > 20


def test_render_prompt_substitutes_variables():
    template = "Hello {name}, value={value}"
    rendered = render_prompt(template, {"name": "Alpha", "value": 42})
    assert "Alpha" in rendered
    assert "42" in rendered


def test_get_prompt_unknown_version():
    with pytest.raises(ValueError):
        get_prompt(InsightType.STRATEGY_EXPLANATION, version="v999")


@pytest.mark.asyncio
async def test_mock_llm_returns_markdown():
    provider = MockLLMProvider()
    response = await provider.complete(
        "unused prompt",
        insight_type=InsightType.STRATEGY_EXPLANATION,
        context={
            "strategy_name": "Premium Alpha",
            "strategy_type": "dsl",
            "parameters": {},
            "source_code": "name: paid\nsignals: []\n",
        },
    )
    assert response.content.startswith("# Strategy insight:")
    assert "no trading signals" in response.content.lower()
    assert "Provide:" not in response.content
    assert response.model == "mock-llm-v1"
    assert response.prompt_tokens > 0
