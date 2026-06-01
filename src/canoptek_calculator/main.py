from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api.routes_api import router as api_router
from .api.routes_html import router as html_router
from .config import get_settings
from .db import initialize_database
from .ingest.service import DataImportService


def create_app() -> FastAPI:
    settings = get_settings()
    package_root = Path(__file__).resolve().parent
    static_dir = package_root / "static"

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database()
        settings.fixtures_dir.mkdir(parents=True, exist_ok=True)
        if settings.auto_sync_on_startup:
            DataImportService.from_defaults().bootstrap()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(html_router)
    app.include_router(api_router, prefix="/api", tags=["api"])

    return app


app = create_app()
