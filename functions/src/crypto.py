"""AES-GCM encryption for response link payloads."""

from __future__ import annotations

import base64
import json
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.models import AppError, LinkPayload


def generate_encryption_key() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")


def _decode_key(key_b64: str) -> bytes:
    key = base64.urlsafe_b64decode(key_b64.encode("ascii"))
    if len(key) != 32:
        raise AppError("Invalid encryption key", status_code=500)
    return key


def encrypt_payload(payload: LinkPayload | dict[str, Any], key_b64: str) -> str:
    data = payload.to_dict() if isinstance(payload, LinkPayload) else payload
    key = _decode_key(key_b64)
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, json.dumps(data, separators=(",", ":")).encode(), None)
    blob = nonce + ciphertext
    return base64.urlsafe_b64encode(blob).decode("ascii").rstrip("=")


def decrypt_payload(token: str, key_b64: str) -> LinkPayload:
    try:
        padding = "=" * (-len(token) % 4)
        blob = base64.urlsafe_b64decode((token + padding).encode("ascii"))
        nonce, ciphertext = blob[:12], blob[12:]
        key = _decode_key(key_b64)
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        data = json.loads(plaintext.decode())
        return LinkPayload.from_dict(data)
    except Exception as exc:
        raise AppError("Invalid or expired response link.", status_code=400) from exc
