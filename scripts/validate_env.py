#!/usr/bin/env python3
"""
Validate that required environment variables are set before starting the application.

Usage:
    python scripts/validate_env.py            # reads .env in the repo root
    python scripts/validate_env.py --prod     # stricter checks for production
    APP_ENV=production python scripts/validate_env.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


ALWAYS_REQUIRED: list[tuple[str, str]] = [
    ("DATABASE_URL", "postgresql+asyncpg:// connection string"),
    ("REDIS_URL", "Redis connection URL (redis://...)"),
    ("JWT_SECRET_KEY", "Secret key for signing JWT tokens"),
    ("APP_SECRET_KEY", "Application secret key"),
]

PROD_REQUIRED: list[tuple[str, str]] = [
    ("CREDENTIALS_ENCRYPTION_KEY", "Fernet key for encrypting broker credentials"),
]

INSECURE_DEFAULTS = {
    "JWT_SECRET_KEY": {"change-me-jwt-secret-key", "secret", "test-secret-key"},
    "APP_SECRET_KEY": {"change-me-in-production-use-a-long-random-string", "secret"},
}


def validate(*, prod: bool = False) -> list[str]:
    errors: list[str] = []

    for var, desc in ALWAYS_REQUIRED:
        value = os.environ.get(var, "")
        if not value:
            errors.append(f"MISSING  {var}  — {desc}")

    if prod:
        for var, desc in PROD_REQUIRED:
            value = os.environ.get(var, "")
            if not value:
                errors.append(f"MISSING  {var}  — {desc} [required in production]")

        for var, insecure in INSECURE_DEFAULTS.items():
            value = os.environ.get(var, "")
            if value in insecure:
                errors.append(
                    f"INSECURE {var}  — value looks like a development placeholder; "
                    "generate a strong random secret for production"
                )

        if os.environ.get("APP_DEBUG", "false").lower() in ("true", "1", "yes"):
            errors.append(
                "INSECURE APP_DEBUG=true  — disable debug mode in production"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate AlphaEdge environment variables")
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Apply stricter production checks",
        default=os.environ.get("APP_ENV", "development") == "production",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    _load_dotenv(repo_root / ".env")

    errors = validate(prod=args.prod)

    if errors:
        print("Environment validation FAILED:\n")
        for e in errors:
            print(f"  ✗ {e}")
        print(
            "\nSee .env.example for documentation on each variable.\n"
            "Run: cp .env.example .env  then fill in the required values."
        )
        sys.exit(1)
    else:
        mode = "production" if args.prod else "development"
        print(f"✓ Environment looks good ({mode} mode)")


if __name__ == "__main__":
    main()
