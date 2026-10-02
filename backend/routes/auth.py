"""
Authentication routes for StudySense.

POST /api/auth/register  — create a new user account
POST /api/auth/login     — exchange credentials for a JWT
GET  /api/auth/me        — return the authenticated user's profile
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import User
from backend.database.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from backend.services.auth_service import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new student account",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    Create a new user account.

    - email and username must be unique
    - password is hashed with Argon2 before storage
    - the plain-text password is never stored or returned
    """
    # Check uniqueness
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{payload.email}' is already registered.",
        )
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' is already taken.",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive a JWT access token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authenticate with email + password and receive a signed JWT.

    The token must be supplied as a ``Bearer`` token in subsequent requests.
    Logout is handled client-side by discarding the token.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    # Use the same error message for wrong email and wrong password to avoid
    # leaking which part of the credentials is incorrect.
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not user.is_active:
        raise invalid
    if not verify_password(payload.password, user.hashed_password):
        raise invalid

    return TokenResponse(access_token=create_access_token(user.id))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Return the profile of the currently authenticated user."""
    return current_user
