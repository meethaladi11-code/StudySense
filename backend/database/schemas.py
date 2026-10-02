"""
Pydantic request / response schemas for StudySense Phases 1, 2, and 3.

Schemas are kept separate from SQLAlchemy models so the API contract is
decoupled from the database layout.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Document schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """API response representation of an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    stored_filename: str
    file_type: str
    collection_name: Optional[str] = None
    chunk_count: int
    is_processed: bool
    created_at: datetime
    user_id: Optional[int] = None


# ── Source / chat schemas ─────────────────────────────────────────────────────

class SourceMetadata(BaseModel):
    """Metadata for a single retrieved document chunk."""

    document_id: Optional[int] = Field(
        None, description="ID of the source document (multi-doc sessions)."
    )
    filename: str
    page: Optional[int] = Field(None, description="0-indexed page from PyMuPDF; null for TXT/DOCX.")
    start_index: Optional[int] = Field(
        None, description="Character offset within the original document."
    )
    content_preview: str = Field(..., description="First 300 chars of the retrieved chunk.")


class ChatRequest(BaseModel):
    """Legacy single-document Q&A request (Phase 1 /api/chat/ask)."""

    document_id: int = Field(..., description="ID of the uploaded document to query.")
    question: str = Field(..., description="The student's question.")


class ChatResponse(BaseModel):
    """Structured answer returned to the student."""

    answer: str
    sources: list[SourceMetadata]


# ── Auth schemas (Phase 2) ────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Registration request."""

    email: str = Field(..., description="Valid e-mail address.")
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, description="Plain-text password (hashed server-side).")


class UserResponse(BaseModel):
    """Safe public representation of a user — never includes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    created_at: datetime
    is_active: bool


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Chat session schemas (Phase 3) ────────────────────────────────────────────

class ChatSessionCreate(BaseModel):
    """Request to create a new study session."""

    title: str = Field(..., min_length=1, max_length=200)
    document_ids: list[int] = Field(
        ..., min_length=1, description="IDs of documents owned by the user to attach."
    )


class ChatSessionSummary(BaseModel):
    """Lightweight session listing (no messages)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessagePublic(BaseModel):
    """A single message with optionally parsed sources."""

    id: int
    role: str
    content: str
    sources: Optional[list[SourceMetadata]] = None
    created_at: datetime


class ChatSessionDetail(BaseModel):
    """Full session: metadata + attached documents + message history."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentResponse]
    messages: list[ChatMessagePublic]


class SessionMessageRequest(BaseModel):
    """New message posted into a session."""

    question: str = Field(..., min_length=1)
