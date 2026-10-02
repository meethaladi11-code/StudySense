"""
Pydantic request / response schemas for StudySense Phase 1.

Schemas are kept separate from SQLAlchemy models so that the API contract
is decoupled from the database representation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Document schemas ──────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """API response representation of an uploaded document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    stored_filename: str
    file_type: str
    collection_name: Optional[str]
    chunk_count: int
    is_processed: bool
    created_at: datetime


# ── Chat schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming question from the student."""

    document_id: int = Field(..., description="ID of the uploaded document to query.")
    question: str = Field(..., description="The student's question.")


class SourceMetadata(BaseModel):
    """Metadata for a single retrieved document chunk used to answer the question."""

    filename: str
    page: Optional[int] = Field(None, description="0-indexed page number from PyMuPDF.")
    start_index: Optional[int] = Field(
        None, description="Character offset within the original document."
    )
    content_preview: str = Field(
        ..., description="First 300 characters of the retrieved chunk."
    )


class ChatResponse(BaseModel):
    """Structured answer returned to the student."""

    answer: str
    sources: list[SourceMetadata]
