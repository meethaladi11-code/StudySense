"""
Analytics routes for StudySense Round 2.

GET /api/analytics/overview      — high-level performance summary
GET /api/analytics/topics        — per-topic accuracy with weak/strong labels
GET /api/analytics/weak-topics   — only weak topics
GET /api/analytics/history       — full attempt history across all quizzes

All deterministic — no LLM involved.
All endpoints require authentication and are scoped to the authenticated user.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.database.models import User
from backend.database.schemas import (
    AnalyticsOverview, AttemptSummary, TopicStat, WeakTopicSummary,
)
from backend.services.analytics_service import (
    get_attempt_history, get_overview, get_topic_stats, get_weak_topics,
)
from backend.services.auth_service import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Get overall performance summary",
)
def analytics_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsOverview:
    """
    Return high-level performance statistics:

    - total quizzes generated
    - total completed attempts
    - average score percentage
    - total questions answered and correct
    """
    return get_overview(current_user.id, db)


@router.get(
    "/topics",
    response_model=list[TopicStat],
    summary="Get per-topic accuracy statistics",
)
def analytics_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TopicStat]:
    """
    Return accuracy, question count, and weak/strong classification
    for every topic the user has been tested on.

    Status values:
      strong            — accuracy >= STRONG_TOPIC_THRESHOLD (default 80%)
      improving         — WEAK <= accuracy < STRONG
      weak              — accuracy < WEAK_TOPIC_THRESHOLD (default 60%)
      insufficient_data — fewer than MIN_TOPIC_QUESTIONS answers
    """
    return get_topic_stats(current_user.id, db)


@router.get(
    "/weak-topics",
    response_model=list[WeakTopicSummary],
    summary="Get topics where accuracy is below the weak threshold",
)
def analytics_weak_topics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WeakTopicSummary]:
    """
    Return only topics where accuracy < WEAK_TOPIC_THRESHOLD and there is
    sufficient data (>= MIN_TOPIC_QUESTIONS answers).  Sorted worst first.
    """
    return get_weak_topics(current_user.id, db)


@router.get(
    "/history",
    response_model=list[AttemptSummary],
    summary="Get full attempt history across all quizzes",
)
def analytics_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttemptSummary]:
    """Return all completed quiz attempts, most recent first."""
    return get_attempt_history(current_user.id, db)
