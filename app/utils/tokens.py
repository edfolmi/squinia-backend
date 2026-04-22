"""Opaque URL token generation and storage hashing."""
from __future__ import annotations

import hashlib
import secrets


def hash_url_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_url_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hex) for one-time links."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_url_token(raw)
