"""
document_service.py — file I/O and PDF processing for StudySense.

Responsibilities:
  - Validate incoming uploads.
  - Safely persist uploaded files to disk.
  - Create Document rows in SQLite.
  - Orchestrate PDF → chunks → embeddings → ChromaDB pipeline.

The heavy LangChain / ChromaDB imports are deferred inside ``process_document``
so that the module can be imported quickly during startup.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.database.models import Document


# ── Constants ─────────────────────────────────────────────────────────────────

_ALLOWED_EXTENSIONS: set[str] = {".pdf"}
_ALLOWED_CONTENT_TYPES: set[str] = {"application/pdf", "binary/octet-stream"}


# ── Validation ────────────────────────────────────────────────────────────────

def validate_pdf(file: UploadFile) -> None:
    """
    Raise HTTPException(400) if the uploaded file is not a PDF.

    Checks both the file extension and the declared content-type.
    The content-type check is lenient because some HTTP clients send
    ``binary/octet-stream`` even for PDF files.
    """
    original_name = file.filename or ""
    suffix = Path(original_name).suffix.lower()

    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only PDF files are accepted in Phase 1.  "
                f"Received file extension: '{suffix or '(none)'}'"
            ),
        )

    content_type = file.content_type or ""
    if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unexpected content-type '{content_type}'.  "
                "Expected 'application/pdf'."
            ),
        )


# ── File I/O ──────────────────────────────────────────────────────────────────

def save_upload_file(file: UploadFile) -> tuple[str, str, str]:
    """
    Persist the uploaded file to the configured upload directory.

    A UUID-based filename is generated to avoid collisions and path-traversal
    risks from untrusted original filenames.

    Returns:
        (original_filename, stored_filename, stored_path)
    """
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    original_filename = file.filename or "upload.pdf"
    suffix = Path(original_filename).suffix.lower() or ".pdf"
    stored_filename = f"{uuid.uuid4().hex}{suffix}"
    stored_path = str(upload_dir / stored_filename)

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with open(stored_path, "wb") as fh:
        fh.write(content)

    return original_filename, stored_filename, stored_path


# ── Database helpers ──────────────────────────────────────────────────────────

def create_document_record(
    db: Session,
    *,
    filename: str,
    stored_filename: str,
    stored_path: str,
    file_type: str,
) -> Document:
    """
    Insert a new Document row (is_processed=False) and return it.
    """
    doc = Document(
        filename=filename,
        stored_filename=stored_filename,
        stored_path=stored_path,
        file_type=file_type,
        is_processed=False,
        chunk_count=0,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ── Processing pipeline ───────────────────────────────────────────────────────

def process_document(db: Session, doc: Document) -> Document:
    """
    Run the full ingestion pipeline for a PDF document:

    1. Load with PyMuPDFLoader
    2. Split with RecursiveCharacterTextSplitter
    3. Attach ``doc_id`` and ``filename`` to every chunk's metadata
    4. Embed with OllamaEmbeddings (all-minilm by default)
    5. Persist in a dedicated ChromaDB collection

    On success, updates ``doc.collection_name``, ``doc.chunk_count``, and
    ``doc.is_processed = True``.

    On failure, raises HTTPException(503) with the underlying error message.
    ``is_processed`` remains False so callers know the document is unusable.
    """
    # Deferred imports — keep startup fast.
    from langchain_community.document_loaders import PyMuPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_ollama import OllamaEmbeddings
    from langchain_chroma import Chroma

    collection_name = f"studysense_doc_{doc.id}"

    try:
        # ── 1. Load ───────────────────────────────────────────────────────
        loader = PyMuPDFLoader(doc.stored_path)
        raw_docs = loader.load()

        if not raw_docs:
            raise ValueError("PyMuPDFLoader returned no pages — the PDF may be empty or image-only.")

        # ── 2. Split ──────────────────────────────────────────────────────
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            add_start_index=True,
        )
        chunks = splitter.split_documents(raw_docs)

        if not chunks:
            raise ValueError("Text splitter produced zero chunks — the PDF may contain no extractable text.")

        # ── 3. Enrich metadata ────────────────────────────────────────────
        for chunk in chunks:
            chunk.metadata["doc_id"] = doc.id
            chunk.metadata["filename"] = doc.filename
            # PyMuPDF already adds "page" (0-indexed) and "source" keys.

        # ── 4. Embed & persist ────────────────────────────────────────────
        embeddings = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
        )
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            persist_directory=settings.vector_db_dir,
        )

    except HTTPException:
        raise  # pass through validation errors untouched
    except Exception as exc:
        # Do NOT mark is_processed=True on failure
        raise HTTPException(
            status_code=503,
            detail=(
                f"Document processing failed: {exc}  "
                "Ensure Ollama is running and the configured embedding model is available."
            ),
        ) from exc

    # ── 5. Update record ──────────────────────────────────────────────────
    doc.collection_name = collection_name
    doc.chunk_count = len(chunks)
    doc.is_processed = True
    db.commit()
    db.refresh(doc)
    return doc
