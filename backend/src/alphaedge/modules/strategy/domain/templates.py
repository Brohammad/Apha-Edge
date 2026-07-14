"""Strategy template gallery."""

from __future__ import annotations

TEMPLATES: dict[str, dict[str, str]] = {
    "sma_crossover": {
        "name": "SMA Crossover",
        "description": "Buy when fast SMA crosses above slow SMA",
        "dsl": (
            "signals:\n"
            "  - when: crossover(sma(close, 10), sma(close, 30))\n"
            "    then: BUY\n"
            "  - when: crossunder(sma(close, 10), sma(close, 30))\n"
            "    then: SELL\n"
        ),
    },
    "rsi_mean_reversion": {
        "name": "RSI Mean Reversion",
        "description": "Buy oversold, sell overbought",
        "dsl": (
            "signals:\n"
            "  - when: rsi(close, 14) < 30\n"
            "    then: BUY\n"
            "  - when: rsi(close, 14) > 70\n"
            "    then: SELL\n"
        ),
    },
}


def list_templates() -> list[dict[str, str]]:
    return [
        {"id": k, "name": v["name"], "description": v["description"]}
        for k, v in TEMPLATES.items()
    ]


def get_template(template_id: str) -> dict[str, str] | None:
    return TEMPLATES.get(template_id)
