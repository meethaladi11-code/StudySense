"""
Document management routes for StudySense Phase 1.

POST /api/documents/upload  — upload and process a PDF
GET  /api/documents         — list all uploaded documents
GET  /api/documents/{id}    — retrieve a single document's metadata
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Document
from backend.database.schemas import DocumentResponse
from backend.services.document_service import (
    create_document_record,
    process_document,
    save_upload_file,
    validate_pdf,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload and process a PDF study document",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload."),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """
    Upload a PDF, persist it to disk, chunk it, embed it with Ollama, and
    store the resulting embeddings in a dedicated ChromaDB collection.

    **Phase 1 limitation**: processing is synchronous.  Large PDFs (~200+ pages)
    may cause the request to take 30–120 seconds depending on hardware.
    Background task support will be added in a later phase.

    Returns the created Document record including ``chunk_count`` and
    ``is_processed=true`` on success.
    """
    validate_pdf(file)

    original_filename, stored_filename, stored_path = save_upload_file(file)

    doc = create_document_record(
        db=db,
        filename=original_filename,
        stored_filename=stored_filename,
        stored_path=stored_path,
        file_type="pdf",
    )

    # process_document raises HTTPException on failure; is_processed stays
    # False so the document cannot be queried in a broken state.
    doc = process_document(db=db, doc=doc)

    return doc  # type: ignore[return-value]


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List all uploaded documents",
)
def list_documents(db: Session = Depends(get_db)) -> list[Document]:
    """Return all uploaded documents ordered by most recently uploaded first."""
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a single document by ID",
)
def get_document(document_id: int, db: Session = Depends(get_db)) -> Document:
    """Return metadata for the document with the given ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document with id={document_id} not found.",
        )
    return doc
