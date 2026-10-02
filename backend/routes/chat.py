"""
RAG chat route for StudySense Phase 1.

POST /api/chat/ask — ask a question about an uploaded document
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import Document
from backend.database.schemas import ChatRequest, ChatResponse
from backend.services.rag_service import get_answer

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Ask a question about an uploaded study document",
)
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Submit a question about a previously uploaded and processed document.

    The answer is grounded exclusively in the document's content via
    semantic retrieval from ChromaDB.  The response also includes source
    chunk metadata (page number, start index, content preview) so the
    student can locate the relevant section in their study material.

    Errors returned:
    - **400** if the question is empty.
    - **400** if the document has not finished processing.
    - **404** if the document_id does not exist.
    - **503** if Ollama is unreachable or the LLM call fails.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    doc: Document | None = (
        db.query(Document).filter(Document.id == request.document_id).first()
    )
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document with id={request.document_id} not found.",
        )
    if not doc.is_processed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Document {request.document_id} ('{doc.filename}') has not been "
                "successfully processed yet.  "
                "Check GET /api/documents/{id} for its current status."
            ),
        )

    try:
        return get_answer(doc=doc, question=request.question)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to generate an answer: {exc}",
        ) from exc
