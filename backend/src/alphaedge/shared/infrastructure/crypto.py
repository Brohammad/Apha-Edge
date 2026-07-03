"""Application-level encryption for sensitive stored credentials."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_json(data: dict[str, Any], secret: str) -> dict[str, Any]:
    if not secret:
        return data
    token = _fernet(secret).encrypt(json.dumps(data).encode())
    return {"_enc": token.decode()}


def decrypt_json(data: dict[str, Any], secret: str) -> dict[str, Any]:
    if "_enc" not in data:
        return data
    if not secret:
        raise ValueError("Encrypted credentials require CREDENTIALS_ENCRYPTION_KEY")
    try:
        plaintext = _fernet(secret).decrypt(data["_enc"].encode())
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt stored credentials") from exc
    parsed = json.loads(plaintext)
    if not isinstance(parsed, dict):
        raise ValueError("Decrypted credentials must be a JSON object")
    return parsed
