"""
Health check routes for StudySense.

GET /api/health        — confirm the API process is alive.
GET /api/health/ollama — confirm Ollama is reachable and models are available.
"""

import httpx
from fastapi import APIRouter

from backend.config.settings import settings

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("", summary="API liveness check")
async def health_check():
    """Returns a simple ``ok`` status to confirm the StudySense API is running."""
    return {"status": "ok", "service": "StudySense API"}


@router.get("/ollama", summary="Ollama connectivity and model check")
async def ollama_health():
    """
    Verify that the Ollama service is reachable and that both the configured
    LLM model and the embedding model are pulled and available.

    This endpoint never crashes the API — Ollama connectivity issues are
    reported as structured JSON fields rather than HTTP errors.
    """
    result: dict = {
        "ollama_url": settings.ollama_base_url,
        "ollama_reachable": False,
        "llm_model": settings.ollama_llm_model,
        "llm_model_available": False,
        "embedding_model": settings.ollama_embedding_model,
        "embedding_model_available": False,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")

        if response.status_code == 200:
            result["ollama_reachable"] = True
            available_names = [m["name"] for m in response.json().get("models", [])]
            result["llm_model_available"] = settings.ollama_llm_model in available_names
            result["embedding_model_available"] = (
                settings.ollama_embedding_model in available_names
            )
    except Exception as exc:
        result["error"] = str(exc)

    return result
