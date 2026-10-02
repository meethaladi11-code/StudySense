"""
quiz_service.py — AI quiz generation for StudySense.

Responsibilities:
  1. Retrieve relevant study-material chunks from ChromaDB.
  2. Build a structured prompt asking the LLM to output valid JSON MCQs.
  3. Parse, validate and sanitise the LLM response.
  4. Retry once if the first response is malformed.
  5. Persist validated questions to the database.

IMPORTANT SAFETY RULES:
  - Never use eval() on LLM output.
  - Always validate structure before saving.
  - Do not save a partially broken quiz.
  - Low temperature for reliable structured output.
"""

import json
import re
from typing import Optional

from fastapi import HTTPException
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.models import Document, Quiz, QuizDocument, QuizQuestion
from backend.database.schemas import SourceMetadata


# ── Prompt ────────────────────────────────────────────────────────────────────

_QUIZ_PROMPT = """\
You are a JSON quiz generator. Your ONLY job is to output a JSON array of multiple-choice questions.

Generate exactly {num_questions} questions based ONLY on the study material below.
Focus topic: {topic_hint}
Difficulty: {difficulty}

STRICT RULES:
1. Output MUST start with [ and end with ]
2. Output ONLY the JSON array — absolutely no text before or after
3. No markdown, no code fences, no explanation, no preamble
4. Every question needs exactly 4 options: A, B, C, D
5. correct_answer must be A, B, C, or D
6. All questions must come from the study material only
7. difficulty must be: easy, medium, or hard

--- Study Material ---
{context}
--- End Study Material ---

Required JSON format:
[
  {{"question":"...","options":{{"A":"...","B":"...","C":"...","D":"..."}},"correct_answer":"A","topic":"...","difficulty":"medium","explanation":"..."}}
]

Output the JSON array now, starting with [:
"""


# ── ChromaDB retrieval helper ─────────────────────────────────────────────────

def retrieve_quiz_context(
    documents: list[Document],
    topic_hint: Optional[str] = None,
) -> tuple[str, list[SourceMetadata]]:
    """
    Retrieve up to MAX_QUIZ_CONTEXT_CHUNKS chunks across all documents.

    Uses topic_hint as the retrieval query when provided (targeted practice),
    otherwise uses a generic "main topics" query.

    Returns:
        (context_string, list[SourceMetadata])
    """
    query = topic_hint if topic_hint else "main topics key concepts definitions"
    max_chunks = settings.max_quiz_context_chunks
    k_per_doc = max(2, max_chunks // len(documents))

    embeddings = OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )

    all_scored: list[tuple[float, object]] = []

    for doc in documents:
        vs = Chroma(
            collection_name=doc.collection_name,
            embedding_function=embeddings,
            persist_directory=settings.vector_db_dir,
        )
        try:
            results = vs.similarity_search_with_score(query, k=k_per_doc)
            for chunk, distance in results:
                relevance = 1.0 / (1.0 + distance)
                chunk.metadata.setdefault("doc_id", doc.id)
                chunk.metadata.setdefault("filename", doc.filename)
                all_scored.append((relevance, chunk))
        except Exception:
            fallback = vs.similarity_search(query, k=k_per_doc)
            for chunk in fallback:
                chunk.metadata.setdefault("doc_id", doc.id)
                chunk.metadata.setdefault("filename", doc.filename)
                all_scored.append((0.5, chunk))

    if not all_scored:
        return "", []

    all_scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for _, chunk in all_scored[:max_chunks]]

    context_parts = [
        f"[From: {c.metadata.get('filename', 'unknown')}]\n{c.page_content}"
        for c in top_chunks
    ]
    context = "\n\n---\n\n".join(context_parts)

    sources = [
        SourceMetadata(
            document_id=c.metadata.get("doc_id"),
            filename=c.metadata.get("filename", "unknown"),
            page=c.metadata.get("page"),
            start_index=c.metadata.get("start_index"),
            content_preview=c.page_content[:300].strip(),
        )
        for c in top_chunks
    ]
    return context, sources


# ── JSON parsing and validation ───────────────────────────────────────────────

def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences that the LLM may wrap around JSON."""
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


_VALID_ANSWERS = {"A", "B", "C", "D"}
_VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def _validate_question(q: dict, idx: int) -> dict:
    """
    Validate a single question dict from the LLM.
    Raises ValueError with a descriptive message on any failure.
    """
    for field in ("question", "options", "correct_answer", "topic", "difficulty", "explanation"):
        if field not in q:
            raise ValueError(f"Question {idx}: missing field '{field}'")

    if not isinstance(q["options"], dict):
        raise ValueError(f"Question {idx}: 'options' must be a dict")

    for key in ("A", "B", "C", "D"):
        if key not in q["options"]:
            raise ValueError(f"Question {idx}: missing option '{key}'")

    ca = str(q["correct_answer"]).strip().upper()
    if ca not in _VALID_ANSWERS:
        raise ValueError(f"Question {idx}: correct_answer '{ca}' not in A/B/C/D")
    q["correct_answer"] = ca

    diff = str(q.get("difficulty", "medium")).strip().lower()
    if diff not in _VALID_DIFFICULTIES:
        diff = "medium"
    q["difficulty"] = diff

    return q


def _parse_llm_output(raw: str, num_questions: int) -> list[dict]:
    """
    Parse and validate the LLM's JSON response.

    Strips code fences, loads JSON, validates each question structure.
    Raises ValueError on any failure so the caller can retry or propagate.
    """
    cleaned = _strip_code_fences(raw)

    # Find the first '[' and last ']' to handle leading/trailing prose
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        # Attempt to wrap a single object in an array
        obj_start = cleaned.find("{")
        obj_end = cleaned.rfind("}")
        if obj_start != -1 and obj_end != -1:
            cleaned = "[" + cleaned[obj_start : obj_end + 1] + "]"
            start, end = 0, len(cleaned) - 1
        else:
            raise ValueError(f"No JSON array found in LLM output. Raw (first 300 chars): {raw[:300]}")

    json_slice = cleaned[start : end + 1]

    try:
        questions = json.loads(json_slice)
    except json.JSONDecodeError as exc:
        # Try stripping control characters and retry
        json_slice_clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", json_slice)
        try:
            questions = json.loads(json_slice_clean)
        except json.JSONDecodeError:
            raise ValueError(f"JSON decode error: {exc}") from exc

    if not isinstance(questions, list):
        raise ValueError("LLM output is not a JSON array.")

    if len(questions) < 1:
        raise ValueError("LLM returned an empty question list.")

    validated = []
    for i, q in enumerate(questions):
        validated.append(_validate_question(q, i + 1))

    return validated


# ── LLM call with retry ───────────────────────────────────────────────────────

def _call_llm_for_quiz(
    context: str,
    num_questions: int,
    difficulty: str,
    topic_hint: Optional[str],
) -> list[dict]:
    """
    Call the Ollama LLM, parse the response.
    Retries once on malformed output.
    Raises HTTPException(503) on Ollama failure.
    Raises HTTPException(500) if both attempts produce invalid JSON.
    """
    llm = OllamaLLM(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,   # low temperature for reliable structured output
    )

    prompt = _QUIZ_PROMPT.format(
        num_questions=num_questions,
        difficulty=difficulty,
        topic_hint=topic_hint or "general",
        context=context,
    )

    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            raw = llm.invoke(prompt)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Ollama is unavailable or returned an error: {exc}",
            ) from exc

        try:
            return _parse_llm_output(raw, num_questions)
        except ValueError as exc:
            last_error = exc
            # Retry once

    raise HTTPException(
        status_code=500,
        detail=(
            f"LLM returned invalid quiz JSON after 2 attempts. "
            f"Last error: {last_error}. "
            "Try reducing num_questions or uploading more study material."
        ),
    )


# ── Main quiz generation entry point ─────────────────────────────────────────

def generate_and_save_quiz(
    db: Session,
    *,
    user_id: int,
    title: str,
    documents: list[Document],
    num_questions: int,
    difficulty: str,
    quiz_type: str = "standard",
    target_topic: Optional[str] = None,
    improvement_plan_id: Optional[int] = None,
) -> Quiz:
    """
    Full quiz generation pipeline:

    1. Retrieve relevant chunks from all documents.
    2. Call the LLM with a structured JSON prompt.
    3. Parse and validate the output.
    4. Persist the Quiz, QuizDocuments, and QuizQuestions.

    Returns the saved Quiz ORM object.
    Raises HTTPException on any failure — the DB is never partially written.
    """
    if not documents:
        raise HTTPException(status_code=400, detail="At least one document is required.")

    # 1. Retrieve context
    context, context_sources = retrieve_quiz_context(documents, topic_hint=target_topic)
    if not context.strip():
        raise HTTPException(
            status_code=400,
            detail="No content could be retrieved from the selected documents.",
        )

    # 2 + 3. Call LLM and validate
    questions_data = _call_llm_for_quiz(context, num_questions, difficulty, target_topic)

    # 4. Persist — only after full validation
    quiz = Quiz(
        user_id=user_id,
        title=title,
        quiz_type=quiz_type,
        target_topic=target_topic,
        improvement_plan_id=improvement_plan_id,
    )
    db.add(quiz)
    db.flush()  # get quiz.id

    for doc in documents:
        db.add(QuizDocument(quiz_id=quiz.id, document_id=doc.id))

    for qdata in questions_data:
        # Build per-question source JSON (use context_sources as proxy)
        sources_json = json.dumps([s.model_dump() for s in context_sources[:2]])
        db.add(QuizQuestion(
            quiz_id=quiz.id,
            question_text=qdata["question"],
            option_a=qdata["options"]["A"],
            option_b=qdata["options"]["B"],
            option_c=qdata["options"]["C"],
            option_d=qdata["options"]["D"],
            correct_answer=qdata["correct_answer"],
            topic=qdata.get("topic", "General"),
            difficulty=qdata.get("difficulty", "medium"),
            explanation=qdata.get("explanation", ""),
            sources=sources_json,
        ))

    db.commit()
    db.refresh(quiz)
    return quiz
