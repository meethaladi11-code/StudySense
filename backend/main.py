"""
StudySense FastAPI application — Phases 1-5 (Round 1 + Round 2).

Run from the repository root:

    uvicorn backend.main:app --reload

Routers registered:
  /api/health       — liveness + Ollama checks (no auth required)
  /api/auth         — register, login, me
  /api/documents    — upload, list, get (auth required)
  /api/chat         — legacy ask + session endpoints (auth required)
  /api/quizzes      — AI quiz generation, taking, submission (auth required)
  /api/analytics    — performance overview and topic stats (auth required)
  /api/improvement  — weak-topic coach, practice, retest (auth required)
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from backend.config.settings import settings
from backend.database.database import init_db
from backend.routes import auth, chat, documents, health
from backend.routes import quizzes, analytics, improvement


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.vector_db_dir).mkdir(parents=True, exist_ok=True)
    init_db()  # creates all NEW tables; leaves existing tables untouched
    yield


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="StudySense API",
    description=(
        "AI-powered study assistant — Phases 1-5 (Round 1 + Round 2).\n\n"
        "Click **Authorize** (🔒) in Swagger to paste your Bearer token "
        "after calling POST /api/auth/login."
    ),
    version="0.4.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

# Round 1
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)

# Round 2
app.include_router(quizzes.router)
app.include_router(analytics.router)
app.include_router(improvement.router)


# ── Custom OpenAPI — BearerAuth scheme for Swagger Authorize button ───────────

def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste the access_token from POST /api/auth/login",
        }
    }
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[method-assign]
