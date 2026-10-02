"""
improvement_service.py — Weak Topic Coach for StudySense.

Responsibilities:
  1. Validate that a topic is "weak" for the user (uses analytics_service).
  2. Retrieve relevant study-material chunks via ChromaDB.
  3. Generate a personalised study plan using the Ollama LLM.
  4. Persist an ImprovementPlan.
  5. Generate targeted practice / retest quizzes (delegates to quiz_service).
  6. Update ImprovementPlan.latest_accuracy and status after a retest.

Grounding rule: study plan is generated from the user's own uploaded material,
not from general LLM knowledge.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from langchain_ollama.llms import OllamaLLM
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.models import (
    Document, ImprovementPlan, Quiz, QuizAnswer, QuizAttempt, QuizQuestion
)
from backend.database.schemas import ImprovementPlanResponse, SourceMetadata
from backend.services.analytics_service import get_topic_accuracy, get_topic_stats
from backend.services.quiz_service import generate_and_save_quiz, retrieve_quiz_context


# ── Improvement plan prompt ───────────────────────────────────────────────────

_PLAN_PROMPT = """\
You are StudySense, an AI tutor helping a student improve in a topic they are struggling with.

Topic: {topic}
Student's current accuracy: {accuracy:.1f}%
Incorrect answers were about: {incorrect_context}

Using ONLY the study material provided below, generate a structured improvement plan.

--- Study Material ---
{material_context}
--- End of Study Material ---

Output a JSON object with exactly these keys:
{{
  "focus_areas": ["list", "of", "2-4", "specific sub-topics to improve"],
  "study_plan": "A clear, step-by-step revision plan in 3-5 sentences.",
  "recommended_minutes": <integer between 10 and 60>,
  "key_concepts": ["short concept 1", "short concept 2", ...]
}}

Output ONLY the JSON object — no markdown, no commentary.
"""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_user_documents(user_id: int, db: Session) -> list[Document]:
    """Return all processed documents belonging to the user."""
    return (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.is_processed == True)
        .all()
    )


def _get_incorrect_context(user_id: int, topic: str, db: Session) -> str:
    """
    Build a short string describing what the user got wrong in the given topic,
    to give the LLM context about knowledge gaps.
    """
    attempt_ids = [
        a.id for a in db.query(QuizAttempt.id).filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.isnot(None),
        ).all()
    ]
    if not attempt_ids:
        return "general concepts"

    wrong_answers = (
        db.query(QuizAnswer, QuizQuestion.question_text)
        .join(QuizQuestion, QuizAnswer.question_id == QuizQuestion.id)
        .filter(
            QuizAnswer.attempt_id.in_(attempt_ids),
            QuizAnswer.is_correct == False,
            QuizQuestion.topic == topic,
        )
        .limit(5)
        .all()
    )

    if not wrong_answers:
        return "general concepts in this topic"

    snippets = [q_text[:80] for _, q_text in wrong_answers]
    return "; ".join(snippets)


def _strip_fences(text: str) -> str:
    import re
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def _call_plan_llm(
    topic: str,
    accuracy: float,
    incorrect_context: str,
    material_context: str,
) -> dict:
    """Generate and parse the improvement plan from the LLM. Retries once."""
    llm = OllamaLLM(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
    )
    prompt = _PLAN_PROMPT.format(
        topic=topic,
        accuracy=accuracy,
        incorrect_context=incorrect_context,
        material_context=material_context,
    )

    last_err: Optional[Exception] = None
    for _ in range(2):
        try:
            raw = llm.invoke(prompt)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Ollama unavailable: {exc}") from exc

        cleaned = _strip_fences(raw)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            last_err = ValueError("No JSON object in LLM response")
            continue
        try:
            data = json.loads(cleaned[start : end + 1])
            # Validate required keys
            if "focus_areas" not in data or "study_plan" not in data:
                raise ValueError("Missing required keys in plan JSON")
            data["focus_areas"] = [str(f) for f in data.get("focus_areas", [])][:6]
            data["recommended_minutes"] = int(data.get("recommended_minutes", 20))
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            last_err = exc

    raise HTTPException(
        status_code=500,
        detail=f"LLM returned invalid plan JSON after 2 attempts. Last error: {last_err}",
    )


# ── Public API ────────────────────────────────────────────────────────────────

def create_improvement_plan(
    user_id: int,
    topic: str,
    db: Session,
) -> ImprovementPlan:
    """
    Create a new ImprovementPlan for a weak topic.

    Validates:
      - Topic exists in user's analytics
      - Topic has sufficient data (>= MIN_TOPIC_QUESTIONS)
      - Topic is classified as 'weak' or 'improving'

    Generates a grounded study plan from user's own documents.
    """
    # 1. Validate topic has analytics data
    stats = get_topic_stats(user_id, db)
    matched = next((s for s in stats if s.topic.lower() == topic.lower()), None)

    if matched is None:
        raise HTTPException(
            status_code=404,
            detail=f"No quiz data found for topic '{topic}'. "
                   "Complete a quiz covering this topic first.",
        )

    if matched.status == "insufficient_data":
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient data for topic '{topic}'. "
                   f"Answer at least {settings.min_topic_questions} questions first.",
        )

    # Use the canonical topic name from stats (preserves original casing)
    canonical_topic = matched.topic
    current_accuracy = matched.accuracy

    # 2. Get user's documents for retrieval
    user_docs = _get_user_documents(user_id, db)
    if not user_docs:
        raise HTTPException(
            status_code=400,
            detail="No processed documents found. Upload study material first.",
        )

    # 3. Retrieve material for the topic
    material_context, context_sources = retrieve_quiz_context(
        user_docs, topic_hint=canonical_topic
    )
    if not material_context.strip():
        raise HTTPException(
            status_code=400,
            detail=f"Could not retrieve study material for topic '{canonical_topic}'. "
                   "Ensure your uploaded documents cover this topic.",
        )

    # 4. Build incorrect-answer context
    incorrect_context = _get_incorrect_context(user_id, canonical_topic, db)

    # 5. Generate plan via LLM
    plan_data = _call_plan_llm(
        topic=canonical_topic,
        accuracy=current_accuracy,
        incorrect_context=incorrect_context,
        material_context=material_context,
    )

    # 6. Persist
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    plan = ImprovementPlan(
        user_id=user_id,
        topic=canonical_topic,
        baseline_accuracy=current_accuracy,
        latest_accuracy=None,
        focus_areas=json.dumps(plan_data["focus_areas"]),
        study_plan=plan_data["study_plan"],
        recommended_minutes=plan_data["recommended_minutes"],
        source_refs=json.dumps([s.model_dump() for s in context_sources]),
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def plan_to_response(plan: ImprovementPlan) -> ImprovementPlanResponse:
    """Convert an ImprovementPlan ORM object to the API response schema."""
    focus_areas: list[str] = []
    try:
        focus_areas = json.loads(plan.focus_areas) if plan.focus_areas else []
    except Exception:
        pass

    source_refs: Optional[list[SourceMetadata]] = None
    try:
        raw_refs = json.loads(plan.source_refs) if plan.source_refs else None
        if raw_refs:
            source_refs = [SourceMetadata(**r) for r in raw_refs]
    except Exception:
        pass

    accuracy_change: Optional[float] = None
    if plan.latest_accuracy is not None:
        accuracy_change = round(plan.latest_accuracy - plan.baseline_accuracy, 1)

    return ImprovementPlanResponse(
        id=plan.id,
        topic=plan.topic,
        baseline_accuracy=plan.baseline_accuracy,
        latest_accuracy=plan.latest_accuracy,
        accuracy_change=accuracy_change,
        focus_areas=focus_areas,
        study_plan=plan.study_plan,
        recommended_minutes=plan.recommended_minutes,
        source_refs=source_refs,
        status=plan.status,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def generate_practice_quiz(
    plan: ImprovementPlan,
    db: Session,
) -> Quiz:
    """
    Generate a targeted practice quiz for the plan's topic.
    quiz_type = 'practice', improvement_plan_id = plan.id.
    """
    user_docs = _get_user_documents(plan.user_id, db)
    if not user_docs:
        raise HTTPException(status_code=400, detail="No documents available for practice.")

    return generate_and_save_quiz(
        db=db,
        user_id=plan.user_id,
        title=f"Practice: {plan.topic}",
        documents=user_docs,
        num_questions=settings.practice_question_count,
        difficulty="mixed",
        quiz_type="practice",
        target_topic=plan.topic,
        improvement_plan_id=plan.id,
    )


def generate_retest_quiz(
    plan: ImprovementPlan,
    db: Session,
) -> Quiz:
    """
    Generate a retest quiz for the plan's topic.
    quiz_type = 'retest', improvement_plan_id = plan.id.
    A different prompt seed ensures new questions are generated.
    """
    user_docs = _get_user_documents(plan.user_id, db)
    if not user_docs:
        raise HTTPException(status_code=400, detail="No documents available for retest.")

    # Use a slightly different topic hint to encourage different questions
    topic_hint = f"{plan.topic} advanced review assessment"

    return generate_and_save_quiz(
        db=db,
        user_id=plan.user_id,
        title=f"Re-test: {plan.topic}",
        documents=user_docs,
        num_questions=settings.retest_question_count,
        difficulty="mixed",
        quiz_type="retest",
        target_topic=plan.topic,
        improvement_plan_id=plan.id,
    )


def update_plan_after_retest(
    plan: ImprovementPlan,
    retest_score: float,
    db: Session,
) -> ImprovementPlan:
    """
    Update the ImprovementPlan after a retest is submitted.

    Sets latest_accuracy and recalculates status:
      >= STRONG_TOPIC_THRESHOLD → improved
      > baseline but < STRONG  → improving
      otherwise                → active
    """
    plan.latest_accuracy = retest_score

    if retest_score >= settings.strong_topic_threshold:
        plan.status = "improved"
    elif retest_score > plan.baseline_accuracy:
        plan.status = "improving"
    else:
        plan.status = "active"

    plan.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(plan)
    return plan
