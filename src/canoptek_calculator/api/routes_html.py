from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..services.catalog import CatalogService
from .deps import get_db_session

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    settings = get_settings()
    catalog = CatalogService(session)
    stats = catalog.get_dashboard_stats()
    factions = catalog.list_factions()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "settings": settings,
            "stats": stats,
            "stats_payload": stats.model_dump(mode="json"),
            "factions": factions,
            "factions_payload": [faction.model_dump(mode="json") for faction in factions],
            "request": request,
        },
    )
