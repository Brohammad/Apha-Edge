"""Password strength validation."""

from __future__ import annotations

import hashlib
import re

import httpx

from alphaedge.config import settings
from alphaedge.shared.domain.exceptions import ValidationError

_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password123",
        "12345678",
        "123456789",
        "qwerty123",
        "letmein123",
        "welcome123",
        "admin12345",
        "securepass123",
    }
)

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")


def validate_password_strength(password: str) -> None:
    if len(password) < 12:
        raise ValidationError("Password must be at least 12 characters")
    if len(password) > 128:
        raise ValidationError("Password must be at most 128 characters")
    if not _UPPER.search(password):
        raise ValidationError("Password must include an uppercase letter")
    if not _LOWER.search(password):
        raise ValidationError("Password must include a lowercase letter")
    if not _DIGIT.search(password):
        raise ValidationError("Password must include a digit")
    if password.lower() in _COMMON_PASSWORDS:
        raise ValidationError("Password is too common")


async def validate_password_not_breached(password: str) -> None:
    """Optional Have I Been Pwned k-anonymity check (production only)."""
    if settings.is_testing or settings.is_development:
        return
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = digest[:5], digest[5:]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "AlphaEdge-PasswordCheck"},
            )
        if resp.status_code != 200:
            return
        for line in resp.text.splitlines():
            hash_suffix, _ = line.split(":", 1)
            if hash_suffix == suffix:
                raise ValidationError(
                    "This password has appeared in a data breach. Choose a different password."
                )
    except ValidationError:
        raise
    except Exception:
        return
