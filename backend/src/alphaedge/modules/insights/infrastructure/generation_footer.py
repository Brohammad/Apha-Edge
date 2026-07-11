def provider_display_name(provider: str) -> str:
    return {"openai": "OpenAI", "mock": "Mock (local)"}.get(provider, provider)


def append_generation_details(
    content: str,
    *,
    llm_provider: str,
    model: str,
    prompt_version: str,
    prompt_tokens: int,
    completion_tokens: int,
    openai_model_configured: str | None = None,
    llm_provider_configured: str | None = None,
) -> str:
    total = prompt_tokens + completion_tokens
    configured_line = ""
    if llm_provider_configured and llm_provider_configured != llm_provider:
        configured_line = f"- **Provider configured:** `{llm_provider_configured}`\n"

    if llm_provider == "openai":
        model_line = f"- **ChatGPT model:** `{model}`\n"
        if openai_model_configured and openai_model_configured != model:
            model_line = (
                f"- **ChatGPT model (configured):** `{openai_model_configured}`\n"
                f"- **ChatGPT model (API response):** `{model}`\n"
            )
    else:
        model_line = f"- **Model:** `{model}`\n"

    footer = (
        f"\n\n## Generation details\n\n"
        f"- **LLM provider:** {provider_display_name(llm_provider)}\n"
        f"{configured_line}"
        f"{model_line}"
        f"- **Prompt version:** `{prompt_version}`\n"
        f"- **Tokens:** {prompt_tokens} prompt + {completion_tokens} completion "
        f"= **{total}** total\n"
    )
    return content.rstrip() + footer
