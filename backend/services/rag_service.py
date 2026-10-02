"""
rag_service.py — retrieval and answer generation for StudySense.

This module owns all LangChain / Ollama logic:
  - Loading the persistent ChromaDB collection for a document.
  - Performing similarity search to retrieve relevant chunks.
  - Building a study-assistant prompt.
  - Calling the Ollama LLM and returning a structured response.

The existing desktop app's core RAG logic (embeddings → Chroma → OllamaLLM)
is preserved here with the following improvements:
  - ChromaDB is loaded from the persistent vector_db/ directory.
  - The prompt explicitly instructs the model to stay grounded.
  - Source metadata is extracted and returned alongside the answer.
"""

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_ollama.llms import OllamaLLM

from backend.config.settings import settings
from backend.database.models import Document
from backend.database.schemas import ChatResponse, SourceMetadata


# ── Prompt template ───────────────────────────────────────────────────────────

_PROMPT_TEMPLATE = """\
You are StudySense, an AI tutor helping a student understand their uploaded study material.

Rules:
- Answer ONLY using the study material provided below.
- If the answer is clearly present, explain it thoroughly and clearly for a student.
- If the answer cannot be found in the material, respond with:
  "I could not find this topic in the uploaded study material. \
Please check whether the relevant section is included in the uploaded document."
- Do NOT invent, guess, or extrapolate information beyond what is provided.
- Be concise and student-friendly.

--- Study Material ---
{context}
--- End of Study Material ---

Student's Question: {question}

Answer:\
"""


# ── Core function ─────────────────────────────────────────────────────────────

def get_answer(doc: Document, question: str) -> ChatResponse:
    """
    Retrieve relevant chunks from the document's ChromaDB collection and
    generate a grounded answer using the configured Ollama LLM.

    Args:
        doc:      The processed Document ORM object.  Must have
                  ``collection_name`` and ``is_processed == True``.
        question: The student's question (non-empty string).

    Returns:
        A ``ChatResponse`` containing the answer text and a list of source
        chunk metadata objects.

    Raises:
        Any exception from LangChain / Ollama is intentionally propagated so
        the route handler can wrap it in a meaningful HTTPException.
    """
    # ── 1. Load the persistent vector store ──────────────────────────────
    embeddings = OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )
    vectorstore = Chroma(
        collection_name=doc.collection_name,
        embedding_function=embeddings,
        persist_directory=settings.vector_db_dir,
    )

    # ── 2. Retrieve relevant chunks ───────────────────────────────────────
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.retrieval_k},
    )
    retrieved_docs = retriever.invoke(question)

    # ── 3. Build prompt ───────────────────────────────────────────────────
    context = "\n\n---\n\n".join(d.page_content for d in retrieved_docs)
    prompt = _PROMPT_TEMPLATE.format(context=context, question=question)

    # ── 4. Call the LLM ───────────────────────────────────────────────────
    llm = OllamaLLM(
        model=settings.ollama_llm_model,
        base_url=settings.ollama_base_url,
    )
    answer: str = llm.invoke(prompt)

    # ── 5. Build source metadata list ─────────────────────────────────────
    sources = [
        SourceMetadata(
            filename=chunk.metadata.get("filename", doc.filename),
            # PyMuPDF stores 0-indexed page numbers under the "page" key.
            page=chunk.metadata.get("page"),
            # add_start_index=True puts character offset under "start_index".
            start_index=chunk.metadata.get("start_index"),
            content_preview=chunk.page_content[:300].strip(),
        )
        for chunk in retrieved_docs
    ]

    return ChatResponse(answer=answer, sources=sources)
