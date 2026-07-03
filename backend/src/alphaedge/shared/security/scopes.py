"""API key scope and RBAC permission helpers."""

from __future__ import annotations


def api_key_has_scope(scopes: list[str], required: str) -> bool:
    for scope in scopes:
        if scope in ("*", required):
            return True
        if scope.endswith(":*"):
            prefix = scope[:-2]
            if required == prefix or required.startswith(f"{prefix}:"):
                return True
    return False


def required_scope_for_method(method: str) -> str:
    if method.upper() in ("GET", "HEAD", "OPTIONS"):
        return "read:*"
    return "write:*"
