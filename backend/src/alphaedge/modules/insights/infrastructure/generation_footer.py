def append_generation_details(
    content: str,
    *,
    llm_provider: str,
    model: str,
    prompt_version: str,
    prompt_tokens: int,
    completion_tokens: int,
    llm_provider_configured: str | None = None,
) -> str:
    total = prompt_tokens + completion_tokens
    configured_line = ""
    if llm_provider_configured and llm_provider_configured != llm_provider:
        configured_line = f"- **LLM configured:** `{llm_provider_configured}`\n"

    footer = (
        f"\n\n## Generation details\n\n"
        f"- **LLM provider:** `{llm_provider}`\n"
        f"{configured_line}"
        f"- **Model:** `{model}`\n"
        f"- **Prompt version:** `{prompt_version}`\n"
        f"- **Tokens:** {prompt_tokens} prompt + {completion_tokens} completion "
        f"= **{total}** total\n"
    )
    return content.rstrip() + footer
