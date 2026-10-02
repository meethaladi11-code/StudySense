"""
StudySense FastAPI application — Phases 1 + 2 + 3.

Run from the repository root:

    uvicorn backend.main:app --reload

Routers registered:
  /api/health     — liveness + Ollama checks (no auth required)
  /api/auth       — register, login, me
  /api/documents  — upload, list, get (auth required)
  /api/chat       — legacy ask + session endpoints (auth required)

Swagger UI (http://127.0.0.1:8000/docs) includes an "Authorize" button
provided automatically by FastAPI when HTTPBearer is used as a dependency.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from backend.config.settings import settings
from backend.database.database import init_db
from backend.routes import auth, chat, documents, health


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: ensure required directories exist and create all DB tables.
    No model loading at startup — everything is lazy.
    """
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.vector_db_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    yield


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="StudySense API",
    description=(
        "AI-powered study assistant — Phases 1 + 2 + 3.\n\n"
        "Click **Authorize** (🔒) in Swagger to paste your Bearer token "
        "after calling POST /api/auth/login."
    ),
    version="0.3.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

# CORS — permissive for local development.
# TODO (Phase 6): restrict allow_origins to the React dev server origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


# ── Custom OpenAPI — add BearerAuth security scheme ───────────────────────────

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
