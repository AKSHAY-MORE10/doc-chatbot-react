"""Doc Chatbot — FastAPI application with security middleware."""

import logging
import time
from collections import defaultdict
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import persist_settings, settings
from app.ingestion import ingest_file
from app.parent_store import delete_collection as delete_parent_collection
from app.retriever import query
from app.schemas import ChatRequest, ChatResponse, IngestResponse, LLMSettingsRequest, LLMSettingsResponse
from app.vectorstore import get_chroma_client

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Doc Chatbot",
    docs_url=None,      # disable Swagger UI in production
    redoc_url=None,      # disable ReDoc in production
)

BASE_DIR = Path(__file__).resolve().parent.parent
# The React frontend (frontend_react/) builds into frontend_dist/ via `npm run build`
# (see vite.config.js) or the Docker image's frontend build stage. main.py only ever
# touches the built output, never the Vite source.
FRONTEND_DIR = BASE_DIR / "frontend_dist"
INDEX_FILE = FRONTEND_DIR / "index.html"


# ── Security headers middleware ─────────────────────────────


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ── Rate limiting middleware ────────────────────────────────

_rate_buckets: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Simple in-memory sliding-window rate limiter per client IP."""
    if request.url.path in ("/health", "/", "/static"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0  # 1 minute
    rpm = settings.RATE_LIMIT_RPM

    # Prune old entries
    timestamps = _rate_buckets[client_ip]
    _rate_buckets[client_ip] = [t for t in timestamps if now - t < window]

    if len(_rate_buckets[client_ip]) >= rpm:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Rate limit exceeded ({rpm} requests/min). Try again later."},
        )

    _rate_buckets[client_ip].append(now)
    return await call_next(request)


# ── CORS ────────────────────────────────────────────────────


def _parse_origins(raw_origins: str) -> list[str]:
    """Parse comma-separated origins. Never falls back to wildcard ``*``."""
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if not origins:
        logger.warning("ALLOWED_ORIGINS is empty — defaulting to localhost only")
        return ["http://127.0.0.1:8000", "http://localhost:8000"]
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(settings.ALLOWED_ORIGINS),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ── Static files ────────────────────────────────────────────
# Vite's build output is a hashed assets/ folder plus index.html; mount assets/
# directly and serve index.html ourselves at "/" (see root() below) rather than
# mounting FRONTEND_DIR at "/" wholesale, so API routes stay top-level.
if (FRONTEND_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


# ── Startup event ───────────────────────────────────────────

@app.on_event("startup")
def _warn_no_admin_key():
    if not settings.ADMIN_API_KEY.strip():
        logger.warning(
            "⚠️  ADMIN_API_KEY is not set — admin endpoints are OPEN. "
            "Set ADMIN_API_KEY in .env before deploying to production."
        )


# ── Auth dependency ─────────────────────────────────────────


def require_admin_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Enforce admin API-key authentication.

    If ``ADMIN_API_KEY`` is not configured, access is **allowed** for local
    development convenience (a warning is logged at startup).  When a key
    IS configured, it is enforced strictly.
    """
    expected_key = settings.ADMIN_API_KEY.strip()

    # No key configured → open access (local dev mode)
    if not expected_key:
        return

    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


# ── Helpers ─────────────────────────────────────────────────


def _current_llm_settings() -> LLMSettingsResponse:
    return LLMSettingsResponse(
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_MODEL,
        embed_model=settings.EMBED_MODEL,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        api_base_url=settings.LLM_API_BASE_URL,
        gemini_base_url=settings.GEMINI_API_BASE_URL,
        api_key_saved=bool(settings.LLM_API_KEY.strip()),
    )


# ── Routes ──────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    if not INDEX_FILE.exists():
        return JSONResponse(
            status_code=503,
            content={
                "detail": (
                    "Frontend not built. Run `npm install && npm run build` inside "
                    "frontend_react/, or use the Docker image which builds it automatically."
                )
            },
        )
    return FileResponse(INDEX_FILE)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    collection: str = Form(default="default"),
    _: None = Depends(require_admin_key),
):
    allowed = {"application/pdf", "text/plain"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only PDF and TXT files supported")

    content = await file.read()
    max_upload_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_upload_bytes:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    chunks_added = await ingest_file(content, file.filename, collection)
    return IngestResponse(
        collection=collection,
        chunks_added=chunks_added,
        filename=file.filename,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        return query(req.question, req.collection, req.history)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Chat error")
        raise HTTPException(500, str(e))


@app.get("/collections")
def list_collections():
    client = get_chroma_client()
    return {"collections": sorted(c.name for c in client.list_collections())}


@app.delete("/collection/{name}")
def delete_collection(name: str, _: None = Depends(require_admin_key)):
    client = get_chroma_client()
    client.delete_collection(name)
    delete_parent_collection(name)
    return {"deleted": name}


@app.get("/settings/llm", response_model=LLMSettingsResponse)
def read_llm_settings(_: None = Depends(require_admin_key)):
    return _current_llm_settings()


@app.put("/settings/llm", response_model=LLMSettingsResponse)
def update_llm_settings(
    payload: LLMSettingsRequest, _: None = Depends(require_admin_key)
):
    embed_provider = "gemini" if payload.provider == "gemini" else "ollama"
    updates = {
        "LLM_PROVIDER": payload.provider,
        "LLM_MODEL": payload.model,
        "EMBED_MODEL": payload.embed_model,
        "EMBED_PROVIDER": embed_provider,
        "OLLAMA_BASE_URL": payload.ollama_base_url,
        "LLM_API_BASE_URL": payload.api_base_url,
        "GEMINI_API_BASE_URL": payload.gemini_base_url,
        "LLM_API_KEY": payload.api_key if payload.provider != "ollama" else None,
    }
    persist_settings(updates)
    return _current_llm_settings()