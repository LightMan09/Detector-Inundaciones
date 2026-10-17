"""Punto de entrada FastAPI (equivalente a app/main.py del documento)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from rally.api.router import api_router
from rally.config import Settings
from rally.config import settings as default_settings
from rally.core.exceptions import SapoException, sapo_exception_handler
from rally.core.logging import setup_logging
from rally.middleware.logging_middleware import LoggingMiddleware
from rally.middleware.rate_limit import RateLimitMiddleware

REPO_ROOT = Path(__file__).resolve().parents[2]
VISUAL_DIR = REPO_ROOT / "visual"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or default_settings
    setup_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "SAPO: detección de agua y basura en sumideros con visión por computador "
            "sobre cámaras existentes, priorización georreferenciada y despacho de "
            "limpieza preventiva. Piloto: Localidad 10 Engativá / Humedal Jaboque. "
            "Las detecciones llegan como JSON del modelo YOLO (data/live/detecciones.json)."
        ),
    )

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        RateLimitMiddleware, max_requests_per_minute=settings.max_requests_per_minute
    )
    app.add_exception_handler(SapoException, sapo_exception_handler)

    app.include_router(api_router)

    # JSON en vivo del modelo YOLO + mapa (lo que consume la web visual)
    if settings.data_dir.exists():
        app.mount("/data", StaticFiles(directory=settings.data_dir), name="data")

    # Docker 1: visual del usuario (tablero estático)
    if VISUAL_DIR.exists():
        app.mount("/", StaticFiles(directory=VISUAL_DIR, html=True), name="visual")

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("rally.main:app", host="0.0.0.0", port=8000, reload=default_settings.debug)
