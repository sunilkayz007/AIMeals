"""
=========================================================
AIMeals Backend
Core Security

Responsibilities:
    - Hash and verify passwords
    - Create and decode JWT access tokens
    - Create and decode JWT refresh tokens

Dependencies:
    - passlib[bcrypt] for password hashing
    - python-jose[cryptography] for JWT encode/decode

Notes:
    - This module has NO database or FastAPI dependency.
      It only contains pure security primitives so it can
      be safely imported by models, services, and
      dependencies without circular imports.
=========================================================
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.A_config import settings
from app.C_logger import app_logger


# =========================================================
# Password Hashing
# =========================================================

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hashes a plaintext password using bcrypt.

    Usage:
        hashed = hash_password("mypassword")
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a bcrypt hash.

    Usage:
        is_valid = verify_password("mypassword", user.hashed_password)
    """
    return _pwd_context.verify(plain_password, hashed_password)


# =========================================================
# JWT Token Creation
# =========================================================

def create_access_token(subject: str, extra_claims: Optional[dict[str, Any]] = None) -> str:
    """
    Creates a short-lived JWT access token.

    Args:
        subject: Typically the user's id (as a string).
        extra_claims: Optional extra data to embed (e.g. role).

    Usage:
        token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> tuple[str, datetime]:
    """
    Creates a long-lived JWT refresh token.

    Returns:
        A tuple of (token string, expiry datetime).
        The expiry is returned separately so the caller can
        store it alongside the token's hash in the database.

    Usage:
        token, expires_at = create_refresh_token(subject=str(user.id))
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expire


# =========================================================
# Refresh Token Hashing
# =========================================================

def hash_token(raw_token: str) -> str:
    """
    Produces a SHA-256 hex digest of a raw token string.

    Used to store refresh tokens in the database without
    ever persisting the raw token itself. SHA-256 (not
    bcrypt) is used deliberately: this is an exact-match
    lookup against a high-entropy JWT, not a low-entropy
    password requiring brute-force resistance.

    Usage:
        token_hash = hash_token(raw_refresh_token)
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# =========================================================
# JWT Token Decoding
# =========================================================

def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decodes and validates a JWT token.

    Returns:
        The decoded payload dict if valid, otherwise None.
        Does not raise — callers should treat None as
        "invalid or expired token" and respond with 401.

    Usage:
        payload = decode_token(token)
        if payload is None:
            raise HTTPException(status_code=401)
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        app_logger.warning("Token decode failed: invalid or expired token.")
        return None