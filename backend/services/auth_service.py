"""
auth_service.py — password hashing, JWT token management, and the
``get_current_user`` FastAPI dependency for StudySense.

Libraries used:
  - pwdlib[argon2]  — Argon2 password hashing
  - PyJWT           — JWT creation and verification
"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.database import get_db
from backend.database.models import User


# ── Password hashing ──────────────────────────────────────────────────────────

# PasswordHash.recommended() selects Argon2 when pwdlib[argon2] is installed.
_pwd_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Return an Argon2 hash of the given plain-text password."""
    return _pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if ``plain`` matches the stored ``hashed`` password."""
    return _pwd_hash.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(user_id: int) -> str:
    """
    Create a signed JWT access token for the given user ID.

    The token payload contains:
      ``sub`` — string representation of user_id
      ``exp`` — expiry timestamp (UTC)
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.  Raises ``jwt.PyJWTError`` on any failure.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


# ── FastAPI dependency ────────────────────────────────────────────────────────

# HTTPBearer adds the padlock icon and "Authorize" button in Swagger UI.
_bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates the Bearer token.

    Returns the active ``User`` ORM object, or raises:
      - 401 if the token is missing, malformed, or expired
      - 401 if the user no longer exists or is deactivated
    """
    token = credentials.credentials
    try:
        payload = _decode_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = (
        db.query(User)
        .filter(User.id == user_id, User.is_active == True)
        .first()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
