from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "local-demo-secret-change-before-deployment-32chars")
JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
REFRESH_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
if os.getenv("RESQNET_ENV") == "production" and len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET must be at least 32 characters in production")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 310_000)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_MINUTES),
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)


def issue_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    expires = now + timedelta(days=REFRESH_DAYS)
    token = jwt.encode({
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": expires,
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, jti, expires


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    return payload


def create_cancel_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return token, token_hash


def verify_cancel_token(token: str, token_hash: str | None) -> bool:
    if not token_hash:
        return False
    actual = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, token_hash)
