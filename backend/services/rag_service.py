"""
rag_service.py — retrieval and answer generation for StudySense.

Exposes two public functions:

  ``get_answer(doc, question)``
      Single-document Q&A for the legacy /api/chat/ask endpoint.

  ``get_session_answer(documents, question)``
      Multi-document Q&A for chat sessions (Phase 3).
      Retrieves top-k chunks per document, scores them, selects the best
      ``max_context_chunks`` across all documents, then calls the LLM.

Both functions use the same grounded prompt template that instructs the
model to stay within the supplied study material.
"""

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM

from backend.config.settings import settings
from backend.database.models import Document
from backend.database.schemas import ChatResponse, SourceMetadata


# ── Shared prompt template ────────────────────────────────────────────────────

_PROMPT = """\
You are StudySense, an AI tutor helping a student understand their study material.

Rules:
- Answer ONLY using the study material provided below.
- If the answer is clearly present, explain it thoroughly and in a student-friendly way.
- If the answer is NOT found in the material, respond with exactly:
  "I could not find this topic in the uploaded study material. \
Please check whether the relevant section is included in the uploaded document(s)."
- Do NOT invent, guess, or extrapolate beyond what is provided.

--- Study Material ---
{context}
--- End of Study Material ---

Student's Question: {question}

Answer:\
"""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _make_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )


def _make_llm() -> OllamaLLM:
    return OllamaLLM(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
    )


def _load_vectorstore(collection_name: str, embeddings: OllamaEmbeddings) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=settings.vector_db_dir,
    )


def _build_sources(chunks: list, fallback_filename: str, fallback_doc_id: int | None = None) -> list[SourceMetadata]:
    """Convert a list of LangChain Document chunks to SourceMetadata objects."""
    return [
        SourceMetadata(
            document_id=chunk.metadata.get("doc_id", fallback_doc_id),
            filename=chunk.metadata.get("filename", fallback_filename),
            page=chunk.metadata.get("page"),
            start_index=chunk.metadata.get("start_index"),
            content_preview=chunk.page_content[:300].strip(),
        )
        for chunk in chunks
    ]


# ── Single-document Q&A (Phase 1 legacy /api/chat/ask) ───────────────────────

def get_answer(doc: Document, question: str) -> ChatResponse:
    """
    Retrieve relevant chunks from a single document's ChromaDB collection and
    generate a grounded answer using the Ollama LLM.

    Args:
        doc:      Processed Document ORM object (must have collection_name set).
        question: Non-empty question string.

    Returns:
        ChatResponse with the answer and per-chunk source metadata.

    Raises:
        Any LangChain / Ollama exception is propagated to the route handler.
    """
    embeddings = _make_embeddings()
    vectorstore = _load_vectorstore(doc.collection_name, embeddings)

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.retrieval_k},
    )
    retrieved = retriever.invoke(question)

    context = "\n\n---\n\n".join(
        f"[From: {c.metadata.get('filename', doc.filename)}]\n{c.page_content}"
        for c in retrieved
    )
    answer: str = _make_llm().invoke(_PROMPT.format(context=context, question=question))

    return ChatResponse(
        answer=answer,
        sources=_build_sources(retrieved, doc.filename, doc.id),
    )


# ── Multi-document Q&A (Phase 3 session messages) ────────────────────────────

def get_session_answer(
    documents: list[Document],
    question: str,
) -> ChatResponse:
    """
    Retrieve relevant chunks from multiple ChromaDB collections and generate a
    grounded answer.

    Strategy:
      1. For each document, retrieve up to ``retrieval_k_per_document`` chunks
         using similarity_search_with_relevance_scores (score ∈ [0, 1], higher
         is more relevant).
      2. Pool all (score, chunk) pairs across documents.
      3. Sort by score descending and take the top ``max_context_chunks`` chunks.
      4. Build a combined context and call the LLM.

    This keeps context bounded regardless of the number of attached documents.

    Args:
        documents: List of processed Document ORM objects for this session.
        question:  The student's question.

    Returns:
        ChatResponse with grounded answer and multi-document source metadata.
    """
    k_per_doc = settings.retrieval_k_per_document
    max_chunks = settings.max_context_chunks

    embeddings = _make_embeddings()
    all_scored: list[tuple[float, object]] = []  # (relevance_score, LCDocument)

    for doc in documents:
        vectorstore = _load_vectorstore(doc.collection_name, embeddings)
        try:
            results = vectorstore.similarity_search_with_relevance_scores(
                question, k=k_per_doc
            )
            for chunk, score in results:
                # Ensure metadata carries the owning document's info
                chunk.metadata.setdefault("doc_id", doc.id)
                chunk.metadata.setdefault("filename", doc.filename)
                all_scored.append((score, chunk))
        except Exception:
            # Fallback: retrieve without scores (use neutral score 0.5)
            fallback_chunks = vectorstore.similarity_search(question, k=k_per_doc)
            for chunk in fallback_chunks:
                chunk.metadata.setdefault("doc_id", doc.id)
                chunk.metadata.setdefault("filename", doc.filename)
                all_scored.append((0.5, chunk))

    if not all_scored:
        return ChatResponse(
            answer=(
                "I could not find any relevant content in the attached documents "
                "to answer your question."
            ),
            sources=[],
        )

    # Sort by relevance descending, cap at max_chunks
    all_scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [chunk for _, chunk in all_scored[:max_chunks]]

    # Build context with per-chunk attribution
    context_parts = [
        f"[From: {c.metadata.get('filename', 'unknown')}]\n{c.page_content}"
        for c in top_chunks
    ]
    context = "\n\n---\n\n".join(context_parts)

    answer: str = _make_llm().invoke(_PROMPT.format(context=context, question=question))

    return ChatResponse(
        answer=answer,
        sources=_build_sources(top_chunks, fallback_filename="unknown"),
    )
