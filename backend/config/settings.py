"""
StudySense — application configuration.

Values are read from ``backend/.env`` (if present) and then from the
environment, falling back to the defaults listed here.  All defaults are
suitable for local development with Ollama running on localhost.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file relative to this file so the app can be launched
# from any working directory (as long as the package is on sys.path).
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
    # Path is relative to the process CWD (repo root when using uvicorn).
    database_url: str = "sqlite:///./studysense.db"

    # ── Storage ───────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    vector_db_dir: str = "vector_db"

    # ── RAG parameters ────────────────────────────────────────────────────
    chunk_size: int = 1200
    chunk_overlap: int = 100
    retrieval_k: int = 3


# Module-level singleton — import this everywhere.
settings = Settings()
