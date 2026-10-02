"""
Pydantic request / response schemas for StudySense Round 1 + Round 2.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ══════════════════════════════════════════════════════════════════════════════
# ROUND 1 SCHEMAS (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    stored_filename: str
    file_type: str
    collection_name: Optional[str] = None
    chunk_count: int
    is_processed: bool
    created_at: datetime
    user_id: Optional[int] = None


class SourceMetadata(BaseModel):
    document_id: Optional[int] = None
    filename: str
    page: Optional[int] = None
    start_index: Optional[int] = None
    content_preview: str


class ChatRequest(BaseModel):
    document_id: int
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceMetadata]


class UserCreate(BaseModel):
    email: str
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    created_at: datetime
    is_active: bool


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatSessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    document_ids: list[int] = Field(..., min_length=1)


class ChatSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessagePublic(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[list[SourceMetadata]] = None
    created_at: datetime


class ChatSessionDetail(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentResponse]
    messages: list[ChatMessagePublic]


class SessionMessageRequest(BaseModel):
    question: str = Field(..., min_length=1)


# ══════════════════════════════════════════════════════════════════════════════
# ROUND 2 SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

# ── Quiz generation ───────────────────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    document_ids: list[int] = Field(..., min_length=1)
    num_questions: int = Field(..., ge=3, le=20)
    difficulty: str = Field("mixed", description="easy | medium | hard | mixed")


class QuizSummary(BaseModel):
    """Lightweight quiz listing — no questions."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    quiz_type: str
    target_topic: Optional[str] = None
    created_at: datetime
    question_count: int = 0


# ── Student-facing question (NO correct_answer, NO explanation) ───────────────

class QuizQuestionForStudent(BaseModel):
    """
    Safe quiz question for the take endpoint.
    Correct answer and explanation are deliberately excluded.
    """
    question_id: int
    question_text: str
    options: dict[str, str]   # {"A": "...", "B": "...", "C": "...", "D": "..."}
    topic: str
    difficulty: str


class QuizTakeResponse(BaseModel):
    quiz_id: int
    title: str
    questions: list[QuizQuestionForStudent]


# ── Quiz submission ───────────────────────────────────────────────────────────

class AnswerSubmission(BaseModel):
    question_id: int
    selected_answer: str = Field(..., pattern="^[ABCD]$")


class QuizSubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(..., min_length=1)


class ReviewItem(BaseModel):
    """Full review row returned after submission — correct answer revealed here."""
    question_id: int
    question_text: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str
    topic: str
    sources: Optional[list[SourceMetadata]] = None


class QuizSubmitResponse(BaseModel):
    attempt_id: int
    correct_count: int
    total_questions: int
    score_percentage: float
    review: list[ReviewItem]


# ── Attempt history ───────────────────────────────────────────────────────────

class AttemptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quiz_id: int
    started_at: datetime
    submitted_at: Optional[datetime] = None
    correct_count: int
    total_questions: int
    score_percentage: float


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsOverview(BaseModel):
    total_quizzes: int
    total_attempts: int
    average_score: float
    questions_answered: int
    correct_answers: int


class TopicStat(BaseModel):
    topic: str
    questions_answered: int
    correct: int
    accuracy: float
    status: str   # strong | improving | weak | insufficient_data


class WeakTopicSummary(BaseModel):
    topic: str
    accuracy: float
    questions_answered: int
    incorrect: int


# ── Improvement plans ─────────────────────────────────────────────────────────

class ImprovementPlanRequest(BaseModel):
    topic: str = Field(..., min_length=1)


class ImprovementPlanResponse(BaseModel):
    id: int
    topic: str
    baseline_accuracy: float
    latest_accuracy: Optional[float] = None
    accuracy_change: Optional[float] = None   # latest - baseline (computed)
    focus_areas: list[str]
    study_plan: str
    recommended_minutes: int
    source_refs: Optional[list[SourceMetadata]] = None
    status: str
    created_at: datetime
    updated_at: datetime


class PracticeQuizResponse(BaseModel):
    """Response from /practice and /retest: the safe student-facing quiz."""
    quiz_id: int
    title: str
    quiz_type: str
    target_topic: str
    questions: list[QuizQuestionForStudent]
