"""
ORM models for StudySense Phase 1.

Only the Document table is created in Phase 1.
Users, quizzes, analytics, and chat history tables will be added in later phases.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.database import Base


class Document(Base):
    """
    Represents an uploaded study document.

    ``stored_filename`` is a UUID-based name that is safe to use on the
    filesystem regardless of the original file name.
    ``collection_name`` is the ChromaDB collection that holds this document's
    embeddings.  It is set after processing completes.
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
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id!r} filename={self.filename!r} "
            f"processed={self.is_processed!r}>"
        )
