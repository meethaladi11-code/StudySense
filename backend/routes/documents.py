"""
Document management routes for StudySense (Phase 1 + 2 + 3).

All endpoints now require authentication.
Document visibility is strictly scoped to the authenticated user.

POST /api/documents/upload  — upload and process PDF / TXT / DOCX
GET  /api/documents         — list the current user's documents only
GET  /api/documents/{id}    — get one document (owner only)
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Document, User
from backend.database.schemas import DocumentResponse
from backend.services.auth_service import get_current_user
from backend.services.document_service import (
    create_document_record,
    process_document,
    save_upload_file,
    validate_file,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=201,
    summary="Upload and process a study document (PDF / TXT / DOCX)",
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    """
    Upload a study document, chunk it, embed it, and persist in ChromaDB.

    Supported types: PDF, TXT, DOCX.

    **Phase 1 limitation**: processing is synchronous.  Large documents may
    take 30–120 seconds.  The uploaded document is scoped to the authenticated
    user and never visible to other users.
    """
    file_type = validate_file(file)
    original_filename, stored_filename, stored_path = save_upload_file(file)

    doc = create_document_record(
        db=db,
        filename=original_filename,
        stored_filename=stored_filename,
        stored_path=stored_path,
        file_type=file_type,
        user_id=current_user.id,
    )
    doc = process_document(db=db, doc=doc)
    return doc  # type: ignore[return-value]


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List documents belonging to the authenticated user",
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    """
    Return all documents uploaded by the authenticated user, most recent first.
    Legacy Phase 1 documents (user_id=NULL) are NOT returned.
    """
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get a single document (owner only)",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    """
    Return metadata for a specific document.

    Returns 404 if the document does not exist OR belongs to another user
    (the same error code prevents leaking the existence of other users' data).
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found.",
        )
    return doc
