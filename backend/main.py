"""
Skylark BI Agent — application entry point.

Architecture (MRC)
──────────────────
  main.py              App factory + startup validation
  config.py            Centralised settings (pydantic-settings)

  models/
    chat.py            ChatRequest · HistoryMessage · SSE event types
    deal.py            Deal data model
    work_order.py      WorkOrder data model

  routes/
    chat_routes.py     POST /api/chat   — thin HTTP boundary only

  controllers/
    chat_controller.py Drives agent loop · formats SSE frames

  services/
    agent_service.py   Groq Llama 3.3 70B — agentic tool-calling loop
    monday_service.py  Async Monday.com GraphQL client (live, no cache)
    tools_service.py   Tool schemas · async executor · summary builders

  utils/
    normalizer.py      Data cleaning — dates · sectors · currency · nulls
"""
from __future__ import annotations
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # must run before any module reads os.environ / Settings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Allow running from either project root (`uvicorn backend.main:app`) or
# inside backend (`uvicorn main:app`).
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import get_settings
from backend.routes.chat_routes import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate critical configuration on startup; log a summary."""
    cfg = get_settings()

    missing = [
        name for name, val in {
            "MONDAY_API_TOKEN":     cfg.monday_api_token,
            "GROQ_API_KEY":         cfg.groq_api_key,
            "DEALS_BOARD_ID":       cfg.deals_board_id,
            "WORK_ORDERS_BOARD_ID": cfg.work_orders_board_id,
        }.items()
        if not val
    ]

    if missing:
        log.warning("Missing environment variables: %s", ", ".join(missing))
    else:
        log.info(
            "Startup OK | model=%s | deals_board=%s | wo_board=%s",
            cfg.groq_model,
            cfg.deals_board_id,
            cfg.work_orders_board_id,
        )

    yield  # app runs here

    log.info("Shutdown complete")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Skylark BI Agent",
        description=(
            "Monday.com Business Intelligence agent — "
            "live GraphQL API · Groq Llama 3.3 70B · SSE streaming"
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS (allow Vercel frontend + local dev) ───────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # tighten to your Vercel URL after first deploy
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(chat_router)

    # ── Static assets (Vite build output) ────────────────────────────────
    frontend_dir = Path(__file__).parent.parent / "frontend"
    dist_dir     = frontend_dir / "dist"
    assets_dir   = dist_dir / "assets"

    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # ── Frontend SPA (catch-all) ──────────────────────────────────────────
    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_ui(full_path: str) -> HTMLResponse:
        index = dist_dir / "index.html"
        if not index.exists():
            return HTMLResponse("<h1>Frontend not built</h1><p>Run <code>npm run build</code> inside the <code>frontend/</code> folder.</p>", status_code=503)
        return HTMLResponse(content=index.read_text(encoding="utf-8"))

    return app


app = create_app()
