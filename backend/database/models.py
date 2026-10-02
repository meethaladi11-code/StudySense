"""
ORM models for StudySense Phases 1, 2, and 3.

Tables defined here:
  - User            (Phase 2)
  - Document        (Phase 1 — now with nullable user_id FK)
  - ChatSession     (Phase 3)
  - ChatSessionDocument  (Phase 3 — join table)
  - ChatMessage     (Phase 3)

Migration note:
  The ``documents`` table already existed from Phase 1.  The ``user_id`` column
  was added via a manual ALTER TABLE migration (see studysense.db.phase1.bak).
  Existing legacy rows keep ``user_id = NULL`` and are treated as unowned.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.database import Base


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    """Registered StudySense student account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="owner")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="owner"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r}>"


# ── Document ──────────────────────────────────────────────────────────────────

class Document(Base):
    """
    Uploaded study document.

    ``user_id`` is nullable to preserve Phase 1 legacy rows.
    All new uploads must have a valid ``user_id``.
    ``collection_name`` follows the format:
      - Legacy:  studysense_doc_{id}
      - Phase 2+: studysense_user_{user_id}_doc_{id}
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    # Nullable: existing Phase 1 rows keep user_id = NULL.
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True
    )

    owner: Mapped["User | None"] = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id!r} filename={self.filename!r} "
            f"user_id={self.user_id!r} processed={self.is_processed!r}>"
        )


# ── ChatSession ───────────────────────────────────────────────────────────────

class ChatSession(Base):
    """
    A named study session referencing one or more of the user's documents.
    Messages within the session are scoped to the attached documents only.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    session_documents: Mapped[list["ChatSessionDocument"]] = relationship(
        "ChatSessionDocument", back_populates="session", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id!r} title={self.title!r} user_id={self.user_id!r}>"


# ── ChatSessionDocument ───────────────────────────────────────────────────────

class ChatSessionDocument(Base):
    """
    Join table linking a ChatSession to its selected Document(s).
    A session may reference multiple documents; retrieval is scoped to them.
    """

    __tablename__ = "chat_session_documents"

    chat_session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), primary_key=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id"), primary_key=True
    )

    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="session_documents"
    )
    document: Mapped["Document"] = relationship("Document")


# ── ChatMessage ───────────────────────────────────────────────────────────────

class ChatMessage(Base):
    """
    A single message within a ChatSession.

    ``role``    — "user" or "assistant"
    ``content`` — the message text
    ``sources`` — JSON-encoded list of SourceMetadata dicts (assistant only)
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
