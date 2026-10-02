"""
analytics_service.py — deterministic performance analytics for StudySense.

ALL numbers are computed from the database.
No LLM is used for analytics calculations.

Public API:
  get_overview(user_id, db)        → AnalyticsOverview
  get_topic_stats(user_id, db)     → list[TopicStat]
  get_weak_topics(user_id, db)     → list[WeakTopicSummary]
  get_attempt_history(user_id, db) → list[AttemptSummary]
  get_topic_accuracy(user_id, topic, db) → float | None
"""

from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.models import (
    Quiz, QuizAnswer, QuizAttempt, QuizQuestion
)
from backend.database.schemas import (
    AnalyticsOverview, AttemptSummary, TopicStat, WeakTopicSummary
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify_topic(accuracy: float, questions_answered: int) -> str:
    """
    Return topic status string based on configurable thresholds.

    Returns 'insufficient_data' when questions_answered < MIN_TOPIC_QUESTIONS.
    """
    if questions_answered < settings.min_topic_questions:
        return "insufficient_data"
    if accuracy >= settings.strong_topic_threshold:
        return "strong"
    if accuracy >= settings.weak_topic_threshold:
        return "improving"
    return "weak"


def _user_quiz_ids(user_id: int, db: Session) -> list[int]:
    """Return all quiz IDs owned by the user."""
    rows = db.query(Quiz.id).filter(Quiz.user_id == user_id).all()
    return [r[0] for r in rows]


# ── Public analytics functions ────────────────────────────────────────────────

def get_overview(user_id: int, db: Session) -> AnalyticsOverview:
    """
    Compute high-level performance summary for a user.

    All counts are derived from DB rows — never from LLM estimates.
    """
    quiz_ids = _user_quiz_ids(user_id, db)

    total_quizzes = len(quiz_ids)

    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.isnot(None),
        )
        .all()
    )
    total_attempts = len(attempts)

    if total_attempts == 0:
        return AnalyticsOverview(
            total_quizzes=total_quizzes,
            total_attempts=0,
            average_score=0.0,
            questions_answered=0,
            correct_answers=0,
        )

    attempt_ids = [a.id for a in attempts]
    answers = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.attempt_id.in_(attempt_ids))
        .all()
    )

    questions_answered = len(answers)
    correct_answers = sum(1 for a in answers if a.is_correct)
    avg_score = round(sum(a.score_percentage for a in attempts) / total_attempts, 2)

    return AnalyticsOverview(
        total_quizzes=total_quizzes,
        total_attempts=total_attempts,
        average_score=avg_score,
        questions_answered=questions_answered,
        correct_answers=correct_answers,
    )


def get_topic_stats(user_id: int, db: Session) -> list[TopicStat]:
    """
    Compute per-topic accuracy from all submitted quiz attempts.

    Groups QuizAnswer rows by the topic of their QuizQuestion.
    Returns a list sorted by topic name.
    """
    attempt_ids = [
        a.id for a in db.query(QuizAttempt.id).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.isnot(None),
        ).all()
    ]
    if not attempt_ids:
        return []

    # Load all answers with their associated question topics
    answers = (
        db.query(QuizAnswer, QuizQuestion.topic)
        .join(QuizQuestion, QuizAnswer.question_id == QuizQuestion.id)
        .filter(QuizAnswer.attempt_id.in_(attempt_ids))
        .all()
    )

    # Aggregate by topic
    topic_data: dict[str, dict] = {}
    for answer, topic in answers:
        t = topic.strip() if topic else "General"
        if t not in topic_data:
            topic_data[t] = {"total": 0, "correct": 0}
        topic_data[t]["total"] += 1
        if answer.is_correct:
            topic_data[t]["correct"] += 1

    stats: list[TopicStat] = []
    for topic, data in sorted(topic_data.items()):
        total = data["total"]
        correct = data["correct"]
        accuracy = round((correct / total) * 100, 1) if total > 0 else 0.0
        stats.append(TopicStat(
            topic=topic,
            questions_answered=total,
            correct=correct,
            accuracy=accuracy,
            status=_classify_topic(accuracy, total),
        ))

    return stats


def get_weak_topics(user_id: int, db: Session) -> list[WeakTopicSummary]:
    """
    Return only topics classified as 'weak' (accuracy < WEAK_TOPIC_THRESHOLD
    and sufficient data).
    """
    all_stats = get_topic_stats(user_id, db)
    weak = [
        WeakTopicSummary(
            topic=s.topic,
            accuracy=s.accuracy,
            questions_answered=s.questions_answered,
            incorrect=s.questions_answered - s.correct,
        )
        for s in all_stats
        if s.status == "weak"
    ]
    return sorted(weak, key=lambda x: x.accuracy)  # worst first


def get_attempt_history(user_id: int, db: Session) -> list[AttemptSummary]:
    """Return all submitted attempts for the user, most recent first."""
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.isnot(None),
        )
        .order_by(QuizAttempt.submitted_at.desc())
        .all()
    )
    return [AttemptSummary.model_validate(a) for a in attempts]


def get_topic_accuracy(user_id: int, topic: str, db: Session) -> float | None:
    """
    Return the current accuracy percentage for a specific topic, or None
    if there is insufficient data (< MIN_TOPIC_QUESTIONS answers).
    """
    stats = get_topic_stats(user_id, db)
    for s in stats:
        if s.topic.lower() == topic.lower():
            if s.status == "insufficient_data":
                return None
            return s.accuracy
    return None
