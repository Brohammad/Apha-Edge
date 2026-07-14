"""User-defined indicator functions in DSL."""

from __future__ import annotations

from typing import Any

from alphaedge.shared.domain.exceptions import ValidationError


def register_custom_indicator(name: str, body: str, registry: dict[str, Any]) -> None:
    if not name.isidentifier():
        raise ValidationError(f"Invalid custom indicator name: {name}")
    registry[name.lower()] = {"type": "custom", "body": body}


def list_custom_indicators(registry: dict[str, Any]) -> list[str]:
    return sorted(k for k, v in registry.items() if isinstance(v, dict) and v.get("type") == "custom")
