from alphaedge.modules.insights.infrastructure.generation_footer import append_generation_details


def test_append_generation_details():
    content = append_generation_details(
        "# Report\n\nBody text.",
        llm_provider="mock",
        model="mock-llm-v1",
        prompt_version="v1",
        prompt_tokens=100,
        completion_tokens=50,
    )
    assert "## Generation details" in content
    assert "**LLM provider:** `mock`" in content
    assert "**Model:** `mock-llm-v1`" in content
    assert "**Prompt version:** `v1`" in content
    assert "= **150** total" in content
