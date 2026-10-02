"""
Chat routes for StudySense (Phase 1 legacy + Phase 3 sessions).

Phase 1 (retained, now requires auth + ownership check):
  POST /api/chat/ask

Phase 3 (new):
  POST /api/chat/sessions                        — create a session
  GET  /api/chat/sessions                        — list user's sessions
  GET  /api/chat/sessions/{session_id}           — session detail + history
  POST /api/chat/sessions/{session_id}/messages  — ask a question, persist Q+A
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import ChatMessage, ChatSession, ChatSessionDocument, Document, User
from backend.database.schemas import (
    ChatMessagePublic,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionSummary,
    DocumentResponse,
    SessionMessageRequest,
    SourceMetadata,
)
from backend.services.auth_service import get_current_user
from backend.services.rag_service import get_answer, get_session_answer

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ── Helper ─────────────────────────────────────────────────────────────────────

def _get_owned_session(
    session_id: int, current_user: User, db: Session
) -> ChatSession:
    """
    Load a ChatSession that belongs to current_user.
    Returns 404 for both missing sessions and sessions owned by other users.
    """
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat session {session_id} not found.",
        )
    return session


def _parse_message(msg: ChatMessage) -> ChatMessagePublic:
    """Convert a ChatMessage ORM row to a ChatMessagePublic schema object."""
    parsed_sources: list[SourceMetadata] | None = None
    if msg.sources:
        try:
            raw = json.loads(msg.sources)
            parsed_sources = [SourceMetadata(**s) for s in raw]
        except Exception:
            parsed_sources = None
    return ChatMessagePublic(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        sources=parsed_sources,
        created_at=msg.created_at,
    )


# ── Phase 1 legacy endpoint (now requires auth + ownership) ───────────────────

@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="[Legacy] Single-document Q&A — requires authentication",
)
def ask_question(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Ask a question about one of your uploaded documents.

    This is the Phase 1 endpoint, retained for backward compatibility.
    For multi-document and persistent history, use the session endpoints.

    The authenticated user must own the target document.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    doc = (
        db.query(Document)
        .filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id,
        )
        .first()
    )
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {request.document_id} not found.",
        )
    if not doc.is_processed:
        raise HTTPException(
            status_code=400,
            detail=f"Document {request.document_id} has not been successfully processed yet.",
        )

    try:
        return get_answer(doc=doc, question=request.question)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to generate answer: {exc}") from exc


# ── Phase 3: Chat sessions ────────────────────────────────────────────────────

@router.post(
    "/sessions",
    response_model=ChatSessionSummary,
    status_code=201,
    summary="Create a new study session",
)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionSummary:
    """
    Create a new chat session referencing one or more of your documents.

    Every document ID in ``document_ids`` must belong to the authenticated
    user and must be fully processed.  The session cannot retrieve content
    from documents not listed here.
    """
    if not payload.document_ids:
        raise HTTPException(status_code=400, detail="At least one document_id is required.")

    # Validate ownership and processing status of all requested documents
    validated_docs: list[Document] = []
    for doc_id in payload.document_ids:
        doc = (
            db.query(Document)
            .filter(Document.id == doc_id, Document.user_id == current_user.id)
            .first()
        )
        if doc is None:
            raise HTTPException(
                status_code=404,
                detail=f"Document {doc_id} not found or not owned by you.",
            )
        if not doc.is_processed:
            raise HTTPException(
                status_code=400,
                detail=f"Document {doc_id} ('{doc.filename}') has not been processed yet.",
            )
        validated_docs.append(doc)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    session = ChatSession(
        user_id=current_user.id,
        title=payload.title.strip(),
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.flush()  # get session.id before adding join rows

    for doc in validated_docs:
        db.add(ChatSessionDocument(chat_session_id=session.id, document_id=doc.id))

    db.commit()
    db.refresh(session)
    return ChatSessionSummary(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionSummary],
    summary="List the current user's chat sessions",
)
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ChatSessionSummary]:
    """Return all sessions owned by the authenticated user, newest first."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        ChatSessionSummary(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionDetail,
    summary="Get full session detail including documents and message history",
)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionDetail:
    """
    Return session metadata, the list of attached documents, and the complete
    ordered message history.  Only the session owner may access this endpoint.
    """
    session = _get_owned_session(session_id, current_user, db)

    docs = [sd.document for sd in session.session_documents]
    doc_responses = [DocumentResponse.model_validate(d) for d in docs]
    messages = [_parse_message(m) for m in session.messages]

    return ChatSessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        documents=doc_responses,
        messages=messages,
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatResponse,
    summary="Ask a question in a session — retrieves from all attached documents",
)
def post_session_message(
    session_id: int,
    payload: SessionMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """
    Submit a question to the session's multi-document RAG pipeline.

    Processing:
    1. Validate session ownership.
    2. Retrieve top-k chunks per attached document (scored).
    3. Select the best ``max_context_chunks`` across all documents.
    4. Build a grounded prompt and call the Ollama LLM.
    5. Persist the user question and the assistant answer (with sources).
    6. Return the answer + source metadata.

    Context is strictly limited to documents attached to this session.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    session = _get_owned_session(session_id, current_user, db)

    documents = [sd.document for sd in session.session_documents]
    if not documents:
        raise HTTPException(
            status_code=400,
            detail="This session has no attached documents.",
        )

    try:
        result: ChatResponse = get_session_answer(documents=documents, question=question)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to generate answer: {exc}",
        ) from exc

    # Persist user message
    db.add(ChatMessage(session_id=session.id, role="user", content=question))

    # Persist assistant message with serialised sources
    sources_json = json.dumps([s.model_dump() for s in result.sources])
    db.add(
        ChatMessage(
            session_id=session.id,
            role="assistant",
            content=result.answer,
            sources=sources_json,
        )
    )

    # Update session timestamp
    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return result
