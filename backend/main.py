"""
StudySense FastAPI application — Phase 1.

Run from the repository root with:

    uvicorn backend.main:app --reload

The application:
  - Creates SQLite tables on first startup.
  - Ensures uploads/ and vector_db/ directories exist.
  - Registers all Phase 1 routers.
  - Configures CORS for local React development (all origins in dev).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.database.database import init_db
from backend.routes import chat, documents, health


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup / shutdown handler.

    On startup:
      - Create upload and vector DB directories if they do not exist.
      - Run SQLAlchemy create_all (idempotent — safe to call on every restart).

    No heavy model loading or embedding happens here — those are done on the
    first request that needs them.
    """
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.vector_db_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    # Shutdown hooks can be added here in future phases.


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="StudySense API",
    description=(
        "AI-powered study assistant — Phase 1.\n\n"
        "Provides PDF ingestion, persistent ChromaDB embeddings, "
        "and Ollama-powered grounded Q&A."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — permissive for local development.
# TODO (Phase 6): restrict allow_origins to the React dev server origin only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)
