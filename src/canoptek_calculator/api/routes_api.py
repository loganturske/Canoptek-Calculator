from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..ingest.service import DataImportService, DataSyncResult
from ..schemas.api import (
    DashboardStatsRead,
    DatasheetDetailRead,
    DatasheetSummaryRead,
    FactionRead,
    SimulationRequest,
    SimulationResponse,
)
from ..services.catalog import CatalogService
from ..services.simulation import SimulationService
from .deps import get_db_session

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/dashboard", response_model=DashboardStatsRead)
def get_dashboard(session: Session = Depends(get_db_session)) -> DashboardStatsRead:
    return CatalogService(session).get_dashboard_stats()


@router.get("/factions", response_model=list[FactionRead])
def get_factions(session: Session = Depends(get_db_session)) -> list[FactionRead]:
    return CatalogService(session).list_factions()


@router.get("/datasheets", response_model=list[DatasheetSummaryRead])
def get_datasheets(
    search: str | None = Query(default=None, min_length=1),
    faction_id: str | None = Query(default=None),
    limit: int = Query(default=2500, ge=1, le=5000),
    session: Session = Depends(get_db_session),
) -> list[DatasheetSummaryRead]:
    return CatalogService(session).list_datasheets(
        search=search, faction_id=faction_id, limit=limit
    )


@router.get("/datasheets/{datasheet_id}", response_model=DatasheetDetailRead)
def get_datasheet_detail(
    datasheet_id: str,
    session: Session = Depends(get_db_session),
) -> DatasheetDetailRead:
    detail = CatalogService(session).get_datasheet_detail(datasheet_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datasheet {datasheet_id} was not found.",
        )
    return detail


@router.post("/sync", response_model=DataSyncResult)
def sync_wahapedia_data() -> DataSyncResult:
    service = DataImportService.from_defaults()
    return service.sync(refresh_download=True)


@router.post("/simulate", response_model=SimulationResponse)
def simulate_attack(
    request: SimulationRequest,
    session: Session = Depends(get_db_session),
) -> SimulationResponse:
    settings = get_settings()
    if request.trials > settings.max_simulation_trials:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Trials cannot exceed {settings.max_simulation_trials}.",
        )

    simulation_service = SimulationService(session)
    try:
        return simulation_service.simulate(request)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
