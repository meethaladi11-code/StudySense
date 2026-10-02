"""
ORM models for StudySense Phases 1-5 (Round 1 + Round 2).

Tables:
  Phase 1/Round 1 (unchanged):
    User, Document, ChatSession, ChatSessionDocument, ChatMessage

  Round 2 (new):
    Quiz, QuizDocument, QuizQuestion, QuizAttempt, QuizAnswer, ImprovementPlan

Migration note:
  Round 2 adds only NEW tables via create_all().
  Existing tables (users, documents, chat_*) are NOT modified.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.database import Base


# ══════════════════════════════════════════════════════════════════════════════
# ROUND 1 MODELS (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    """Registered StudySense student account."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="owner")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="owner")
    quizzes: Mapped[list["Quiz"]] = relationship("Quiz", back_populates="owner")
    improvement_plans: Mapped[list["ImprovementPlan"]] = relationship("ImprovementPlan", back_populates="owner")


class Document(Base):
    """Uploaded study document."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    owner: Mapped["User | None"] = relationship("User", back_populates="documents")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    session_documents: Mapped[list["ChatSessionDocument"]] = relationship(
        "ChatSessionDocument", back_populates="session", cascade="all, delete-orphan"
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session",
        order_by="ChatMessage.created_at", cascade="all, delete-orphan",
    )


class ChatSessionDocument(Base):
    __tablename__ = "chat_session_documents"

    chat_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), primary_key=True)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="session_documents")
    document: Mapped["Document"] = relationship("Document")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


# ══════════════════════════════════════════════════════════════════════════════
# ROUND 2 MODELS (new)
# ══════════════════════════════════════════════════════════════════════════════

class Quiz(Base):
    """
    A generated MCQ quiz owned by a user.

    quiz_type:
      standard  — normal quiz from documents
      practice  — targeted practice from an ImprovementPlan
      retest    — follow-up test after practice
    """
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    quiz_type: Mapped[str] = mapped_column(String, nullable=False, default="standard")  # standard|practice|retest
    target_topic: Mapped[str | None] = mapped_column(String, nullable=True)
    improvement_plan_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("improvement_plans.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="quizzes")
    quiz_documents: Mapped[list["QuizDocument"]] = relationship(
        "QuizDocument", back_populates="quiz", cascade="all, delete-orphan"
    )
    questions: Mapped[list["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="quiz",
        order_by="QuizQuestion.id", cascade="all, delete-orphan",
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(
        "QuizAttempt", back_populates="quiz", cascade="all, delete-orphan"
    )
    improvement_plan: Mapped["ImprovementPlan | None"] = relationship(
        "ImprovementPlan", back_populates="quizzes", foreign_keys=[improvement_plan_id]
    )


class QuizDocument(Base):
    """Join table: Quiz ↔ Document."""
    __tablename__ = "quiz_documents"

    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id"), primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), primary_key=True)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="quiz_documents")
    document: Mapped["Document"] = relationship("Document")


class QuizQuestion(Base):
    """
    A single MCQ question belonging to a Quiz.

    correct_answer stores 'A', 'B', 'C', or 'D'.
    sources is a JSON string of SourceMetadata dicts.
    difficulty is 'easy', 'medium', or 'hard'.
    """
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(Text, nullable=False)
    option_b: Mapped[str] = mapped_column(Text, nullable=False)
    option_c: Mapped[str] = mapped_column(Text, nullable=False)
    option_d: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(1), nullable=False)  # A/B/C/D
    topic: Mapped[str] = mapped_column(String, nullable=False)
    difficulty: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")
    answers: Mapped[list["QuizAnswer"]] = relationship("QuizAnswer", back_populates="question")


class QuizAttempt(Base):
    """
    One submission of a Quiz by a user.
    Multiple attempts are allowed; old attempts are never overwritten.
    """
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    correct_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="attempts")
    answers: Mapped[list["QuizAnswer"]] = relationship(
        "QuizAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )


class QuizAnswer(Base):
    """One answer row per question per attempt."""
    __tablename__ = "quiz_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("quiz_questions.id"), nullable=False, index=True)
    selected_answer: Mapped[str] = mapped_column(String(1), nullable=False)  # A/B/C/D
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    attempt: Mapped["QuizAttempt"] = relationship("QuizAttempt", back_populates="answers")
    question: Mapped["QuizQuestion"] = relationship("QuizQuestion", back_populates="answers")


class ImprovementPlan(Base):
    """
    A personalised coaching plan for a specific weak topic.

    baseline_accuracy  — accuracy at plan creation time
    latest_accuracy    — updated after each retest submission
    focus_areas        — JSON list of specific sub-topics to revise
    source_refs        — JSON list of SourceMetadata dicts from study material
    status             — active | improving | improved
    """
    __tablename__ = "improvement_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    baseline_accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    latest_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    focus_areas: Mapped[str] = mapped_column(Text, nullable=False)      # JSON list
    study_plan: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    source_refs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="improvement_plans")
    quizzes: Mapped[list["Quiz"]] = relationship(
        "Quiz", back_populates="improvement_plan", foreign_keys="Quiz.improvement_plan_id"
    )
