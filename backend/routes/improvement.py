"""
Improvement Coach routes for StudySense Round 2.

POST /api/improvement/plans                       — create plan for weak topic
GET  /api/improvement/plans                       — list user's plans
GET  /api/improvement/plans/{id}                  — plan detail
POST /api/improvement/plans/{id}/practice         — generate targeted practice quiz
POST /api/improvement/plans/{id}/retest           — generate retest quiz

All authenticated.  All resources scoped to the authenticated user.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import (
    ImprovementPlan, Quiz, QuizAnswer, QuizAttempt, QuizQuestion, User
)
from backend.database.schemas import (
    ImprovementPlanRequest, ImprovementPlanResponse,
    PracticeQuizResponse, QuizQuestionForStudent, SourceMetadata,
)
from backend.services.auth_service import get_current_user
from backend.services.improvement_service import (
    create_improvement_plan,
    generate_practice_quiz,
    generate_retest_quiz,
    plan_to_response,
    update_plan_after_retest,
)

router = APIRouter(prefix="/api/improvement", tags=["Improvement Coach"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_owned_plan(plan_id: int, user: User, db: Session) -> ImprovementPlan:
    plan = db.query(ImprovementPlan).filter(
        ImprovementPlan.id == plan_id,
        ImprovementPlan.user_id == user.id,
    ).first()
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Improvement plan {plan_id} not found.")
    return plan


def _quiz_to_practice_response(quiz: Quiz) -> PracticeQuizResponse:
    """Convert a Quiz ORM object to the student-safe PracticeQuizResponse."""
    questions = [
        QuizQuestionForStudent(
            question_id=q.id,
            question_text=q.question_text,
            options={"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
            topic=q.topic,
            difficulty=q.difficulty,
        )
        for q in quiz.questions
    ]
    return PracticeQuizResponse(
        quiz_id=quiz.id,
        title=quiz.title,
        quiz_type=quiz.quiz_type,
        target_topic=quiz.target_topic or "",
        questions=questions,
    )


def _get_retest_score(quiz: Quiz, user_id: int, db: Session) -> Optional[float]:
    """
    Return the score percentage of the most recent submitted attempt for a quiz.
    Returns None if no submitted attempt exists.
    """
    attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.isnot(None),
        )
        .order_by(QuizAttempt.submitted_at.desc())
        .first()
    )
    return attempt.score_percentage if attempt else None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/plans",
    response_model=ImprovementPlanResponse,
    status_code=201,
    summary="Create a personalised improvement plan for a weak topic",
)
def create_plan(
    payload: ImprovementPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImprovementPlanResponse:
    """
    Generate a study plan grounded in the student's uploaded material.

    Requirements:
    - The topic must appear in the student's quiz analytics.
    - There must be sufficient quiz data (>= MIN_TOPIC_QUESTIONS answers).
    - The student's uploaded documents must contain relevant material.

    Returns a plan with focus areas, study guidance, and source references.
    """
    plan = create_improvement_plan(
        user_id=current_user.id,
        topic=payload.topic.strip(),
        db=db,
    )
    return plan_to_response(plan)


@router.get(
    "/plans",
    response_model=list[ImprovementPlanResponse],
    summary="List your improvement plans",
)
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ImprovementPlanResponse]:
    """Return all improvement plans owned by the authenticated user."""
    plans = (
        db.query(ImprovementPlan)
        .filter(ImprovementPlan.user_id == current_user.id)
        .order_by(ImprovementPlan.created_at.desc())
        .all()
    )
    return [plan_to_response(p) for p in plans]


@router.get(
    "/plans/{plan_id}",
    response_model=ImprovementPlanResponse,
    summary="Get improvement plan detail",
)
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImprovementPlanResponse:
    plan = _get_owned_plan(plan_id, current_user, db)
    return plan_to_response(plan)


@router.post(
    "/plans/{plan_id}/practice",
    response_model=PracticeQuizResponse,
    status_code=201,
    summary="Generate a targeted practice quiz for this topic",
)
def practice_quiz(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeQuizResponse:
    """
    Generate approximately {PRACTICE_QUESTION_COUNT} questions specifically
    targeting the weak topic.  Results from practice attempts are included
    in the user's analytics.
    """
    plan = _get_owned_plan(plan_id, current_user, db)
    quiz = generate_practice_quiz(plan=plan, db=db)
    return _quiz_to_practice_response(quiz)


@router.post(
    "/plans/{plan_id}/retest",
    response_model=PracticeQuizResponse,
    status_code=201,
    summary="Generate a retest quiz to measure improvement",
)
def retest_quiz(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PracticeQuizResponse:
    """
    Generate a fresh retest quiz for the topic.

    After submitting the retest via POST /api/quizzes/{id}/submit,
    the improvement plan's latest_accuracy and status will be updated
    automatically.

    Note: the plan update happens when the retest is SUBMITTED, not here.
    """
    plan = _get_owned_plan(plan_id, current_user, db)
    quiz = generate_retest_quiz(plan=plan, db=db)
    return _quiz_to_practice_response(quiz)
