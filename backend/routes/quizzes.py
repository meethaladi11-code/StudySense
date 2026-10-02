"""
Quiz routes for StudySense Round 2.

POST /api/quizzes/generate       — generate a new quiz from documents
GET  /api/quizzes                — list user's quizzes
GET  /api/quizzes/{id}           — quiz metadata + question count
GET  /api/quizzes/{id}/take      — student-safe questions (no answers)
POST /api/quizzes/{id}/submit    — submit answers, get scored result + review
GET  /api/quizzes/{id}/attempts  — attempt history for one quiz

All endpoints require authentication.
All resources are strictly scoped to the authenticated user.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import (
    Document, Quiz, QuizAnswer, QuizAttempt, QuizQuestion, User
)
from backend.database.schemas import (
    AttemptSummary, QuizGenerateRequest, QuizQuestionForStudent,
    QuizSubmitRequest, QuizSubmitResponse, QuizSummary, QuizTakeResponse,
    ReviewItem, SourceMetadata,
)
from backend.services.auth_service import get_current_user
from backend.services.quiz_service import generate_and_save_quiz
from backend.services.improvement_service import update_plan_after_retest

router = APIRouter(prefix="/api/quizzes", tags=["Quizzes"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_owned_quiz(quiz_id: int, user: User, db: Session) -> Quiz:
    """Load a Quiz owned by the user or raise 404."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.user_id == user.id).first()
    if quiz is None:
        raise HTTPException(status_code=404, detail=f"Quiz {quiz_id} not found.")
    return quiz


def _question_to_student(q: QuizQuestion) -> QuizQuestionForStudent:
    """Convert a QuizQuestion to the student-safe schema (no answer/explanation)."""
    return QuizQuestionForStudent(
        question_id=q.id,
        question_text=q.question_text,
        options={"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
        topic=q.topic,
        difficulty=q.difficulty,
    )


def _parse_sources(sources_json: Optional[str]) -> Optional[list[SourceMetadata]]:
    if not sources_json:
        return None
    try:
        return [SourceMetadata(**s) for s in json.loads(sources_json)]
    except Exception:
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/generate",
    response_model=QuizSummary,
    status_code=201,
    summary="Generate a new AI quiz from your documents",
)
def generate_quiz(
    payload: QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizSummary:
    """
    Generate a multiple-choice quiz grounded in the selected study documents.

    - Every document must be owned by the authenticated user and processed.
    - num_questions must be between 3 and 20.
    - difficulty: easy | medium | hard | mixed
    """
    valid_difficulties = {"easy", "medium", "hard", "mixed"}
    if payload.difficulty not in valid_difficulties:
        raise HTTPException(
            status_code=400,
            detail=f"difficulty must be one of: {', '.join(valid_difficulties)}",
        )

    # Validate ownership and processing status for each document
    documents: list[Document] = []
    for doc_id in payload.document_ids:
        doc = db.query(Document).filter(
            Document.id == doc_id, Document.user_id == current_user.id
        ).first()
        if doc is None:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
        if not doc.is_processed:
            raise HTTPException(
                status_code=400,
                detail=f"Document {doc_id} ('{doc.filename}') is not yet processed.",
            )
        documents.append(doc)

    quiz = generate_and_save_quiz(
        db=db,
        user_id=current_user.id,
        title=payload.title,
        documents=documents,
        num_questions=payload.num_questions,
        difficulty=payload.difficulty,
    )

    return QuizSummary(
        id=quiz.id,
        title=quiz.title,
        quiz_type=quiz.quiz_type,
        target_topic=quiz.target_topic,
        created_at=quiz.created_at,
        question_count=len(quiz.questions),
    )


@router.get(
    "",
    response_model=list[QuizSummary],
    summary="List your quizzes",
)
def list_quizzes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[QuizSummary]:
    """Return all quizzes owned by the authenticated user, newest first."""
    quizzes = (
        db.query(Quiz)
        .filter(Quiz.user_id == current_user.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )
    return [
        QuizSummary(
            id=q.id,
            title=q.title,
            quiz_type=q.quiz_type,
            target_topic=q.target_topic,
            created_at=q.created_at,
            question_count=len(q.questions),
        )
        for q in quizzes
    ]


@router.get(
    "/{quiz_id}",
    response_model=QuizSummary,
    summary="Get quiz metadata",
)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizSummary:
    quiz = _get_owned_quiz(quiz_id, current_user, db)
    return QuizSummary(
        id=quiz.id,
        title=quiz.title,
        quiz_type=quiz.quiz_type,
        target_topic=quiz.target_topic,
        created_at=quiz.created_at,
        question_count=len(quiz.questions),
    )


@router.get(
    "/{quiz_id}/take",
    response_model=QuizTakeResponse,
    summary="Get quiz questions for a student (correct answers NOT included)",
)
def take_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizTakeResponse:
    """
    Return the quiz questions in student-safe format.

    Correct answers and explanations are deliberately excluded from this
    response.  They are only revealed after submission.
    """
    quiz = _get_owned_quiz(quiz_id, current_user, db)
    return QuizTakeResponse(
        quiz_id=quiz.id,
        title=quiz.title,
        questions=[_question_to_student(q) for q in quiz.questions],
    )


@router.post(
    "/{quiz_id}/submit",
    response_model=QuizSubmitResponse,
    summary="Submit quiz answers and receive score + review",
)
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuizSubmitResponse:
    """
    Submit answers for a quiz.

    Score is calculated SERVER-SIDE — client-supplied scores are never trusted.

    Validation:
    - Quiz must be owned by the authenticated user.
    - All question IDs must belong to this quiz.
    - Each question must be answered at most once.
    - selected_answer must be A, B, C, or D.

    Returns scored result and a full review with correct answers revealed.
    """
    quiz = _get_owned_quiz(quiz_id, current_user, db)

    # Build a map of valid question IDs for this quiz
    question_map: dict[int, QuizQuestion] = {q.id: q for q in quiz.questions}

    # Validate submitted answer IDs
    seen_question_ids: set[int] = set()
    for ans in payload.answers:
        if ans.question_id not in question_map:
            raise HTTPException(
                status_code=422,
                detail=f"Question ID {ans.question_id} does not belong to quiz {quiz_id}.",
            )
        if ans.question_id in seen_question_ids:
            raise HTTPException(
                status_code=422,
                detail=f"Question ID {ans.question_id} answered more than once.",
            )
        seen_question_ids.add(ans.question_id)

    # Create attempt record
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        started_at=now,
        submitted_at=now,
        total_questions=len(payload.answers),
    )
    db.add(attempt)
    db.flush()  # get attempt.id

    # Score answers server-side
    correct_count = 0
    review_items: list[ReviewItem] = []

    for ans in payload.answers:
        question = question_map[ans.question_id]
        is_correct = ans.selected_answer.upper() == question.correct_answer.upper()
        if is_correct:
            correct_count += 1

        db.add(QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_answer=ans.selected_answer.upper(),
            is_correct=is_correct,
        ))

        review_items.append(ReviewItem(
            question_id=question.id,
            question_text=question.question_text,
            selected_answer=ans.selected_answer.upper(),
            correct_answer=question.correct_answer,
            is_correct=is_correct,
            explanation=question.explanation,
            topic=question.topic,
            sources=_parse_sources(question.sources),
        ))

    # Finalise attempt stats
    total = len(payload.answers)
    score_pct = round((correct_count / total) * 100, 1) if total > 0 else 0.0
    attempt.correct_count = correct_count
    attempt.score_percentage = score_pct

    db.commit()

    # If this is a retest quiz, update the linked ImprovementPlan
    if quiz.quiz_type == "retest" and quiz.improvement_plan_id is not None:
        from backend.database.models import ImprovementPlan
        plan = db.query(ImprovementPlan).filter(
            ImprovementPlan.id == quiz.improvement_plan_id,
            ImprovementPlan.user_id == current_user.id,
        ).first()
        if plan is not None:
            update_plan_after_retest(plan, score_pct, db)

    return QuizSubmitResponse(
        attempt_id=attempt.id,
        correct_count=correct_count,
        total_questions=total,
        score_percentage=score_pct,
        review=review_items,
    )


@router.get(
    "/{quiz_id}/attempts",
    response_model=list[AttemptSummary],
    summary="Get attempt history for one quiz",
)
def get_quiz_attempts(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttemptSummary]:
    """Return all submitted attempts for the specified quiz (owner only)."""
    quiz = _get_owned_quiz(quiz_id, current_user, db)
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.submitted_at.isnot(None),
        )
        .order_by(QuizAttempt.submitted_at.desc())
        .all()
    )
    return [AttemptSummary.model_validate(a) for a in attempts]
