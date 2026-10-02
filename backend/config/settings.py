"""
StudySense — application configuration.

Values are read from ``backend/.env`` (if present) and then from the
environment, falling back to the defaults listed here.  All defaults are
suitable for local development with Ollama running on localhost.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Ollama ────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2:latest"
    ollama_embedding_model: str = "all-minilm:latest"

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./studysense.db"

    # ── Storage ───────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    vector_db_dir: str = "vector_db"

    # ── RAG — single-document (Phase 1 legacy) ────────────────────────────
    chunk_size: int = 1200
    chunk_overlap: int = 100
    retrieval_k: int = 3

    # ── RAG — multi-document sessions (Phase 3) ───────────────────────────
    retrieval_k_per_document: int = 3   # chunks retrieved per document
    max_context_chunks: int = 6         # hard cap sent to the LLM

    # ── JWT authentication (Phase 2) ──────────────────────────────────────
    # IMPORTANT: override JWT_SECRET_KEY with a long random secret in production.
    #   Generate one with:  python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret_key: str = "CHANGE-ME-GENERATE-WITH-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours


settings = Settings()
