"""Authentication service."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings


def _simple_hash(password: str) -> str:
    """Simple SHA256 hash for development (replace with bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def _simple_verify(plain: str, hashed: str) -> bool:
    """Verify simple hash."""
    return _simple_hash(plain) == hashed


# In-memory user store (replace with DB in production)
USERS_DB: dict[str, dict[str, Any]] = {
    "admin": {
        "id": "user-001",
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": _simple_hash("admin123"),
        "role": "admin",
        "is_active": True,
    },
    "operator1": {
        "id": "user-002",
        "username": "operator1",
        "email": "op1@example.com",
        "hashed_password": _simple_hash("operator123"),
        "role": "operator",
        "is_active": True,
    },
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return _simple_verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return _simple_hash(password)


def get_user(username: str) -> dict[str, Any] | None:
    """Get user by username."""
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Authenticate a user."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token."""
    settings = get_settings()
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Verify an access token and return the payload."""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != "access":
        return None
    return payload


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """Verify a refresh token and return the payload."""
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    return payload
