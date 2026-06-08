from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..ingest.service import DataImportService, DataSyncResult
from ..schemas.api import (
    ArmyListCreate,
    ArmyListDetailRead,
    ArmyListEntryCreate,
    ArmyListEntryUpdate,
    ArmyListSummaryRead,
    ArmyListUpdate,
    DashboardStatsRead,
    DatasheetDetailRead,
    DatasheetSummaryRead,
    FactionRead,
    SimulationBuildPreviewRead,
    SimulationBuildPreviewRequest,
    SimulationRequest,
    SimulationResponse,
)
from ..services.army_lists import ArmyListService
from ..services.catalog import CatalogService
from ..services.simulation import SimulationService
from ..services.unit_builds import UnitBuildService
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


@router.get("/army-lists", response_model=list[ArmyListSummaryRead])
def get_army_lists(session: Session = Depends(get_db_session)) -> list[ArmyListSummaryRead]:
    return ArmyListService(session).list_army_lists()


@router.post(
    "/army-lists",
    response_model=ArmyListDetailRead,
    status_code=status.HTTP_201_CREATED,
)
def create_army_list(
    payload: ArmyListCreate,
    session: Session = Depends(get_db_session),
) -> ArmyListDetailRead:
    service = ArmyListService(session)
    try:
        return service.create_army_list(payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/army-lists/{army_list_id}", response_model=ArmyListDetailRead)
def get_army_list_detail(
    army_list_id: int,
    session: Session = Depends(get_db_session),
) -> ArmyListDetailRead:
    service = ArmyListService(session)
    try:
        return service.get_army_list_detail(army_list_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/army-lists/{army_list_id}", response_model=ArmyListDetailRead)
def update_army_list(
    army_list_id: int,
    payload: ArmyListUpdate,
    session: Session = Depends(get_db_session),
) -> ArmyListDetailRead:
    service = ArmyListService(session)
    try:
        return service.update_army_list(army_list_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.delete("/army-lists/{army_list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_army_list(
    army_list_id: int,
    session: Session = Depends(get_db_session),
) -> Response:
    service = ArmyListService(session)
    try:
        service.delete_army_list(army_list_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/army-lists/{army_list_id}/entries",
    response_model=ArmyListDetailRead,
)
def create_army_list_entry(
    army_list_id: int,
    payload: ArmyListEntryCreate,
    session: Session = Depends(get_db_session),
) -> ArmyListDetailRead:
    service = ArmyListService(session)
    try:
        return service.add_entry(army_list_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.patch(
    "/army-lists/{army_list_id}/entries/{entry_id}",
    response_model=ArmyListDetailRead,
)
def update_army_list_entry(
    army_list_id: int,
    entry_id: int,
    payload: ArmyListEntryUpdate,
    session: Session = Depends(get_db_session),
) -> ArmyListDetailRead:
    service = ArmyListService(session)
    try:
        return service.update_entry(army_list_id, entry_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.delete(
    "/army-lists/{army_list_id}/entries/{entry_id}",
    response_model=ArmyListDetailRead,
)
def delete_army_list_entry(
    army_list_id: int,
    entry_id: int,
    session: Session = Depends(get_db_session),
) -> ArmyListDetailRead:
    service = ArmyListService(session)
    try:
        return service.delete_entry(army_list_id, entry_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/sync", response_model=DataSyncResult)
def sync_wahapedia_data() -> DataSyncResult:
    service = DataImportService.from_defaults()
    return service.sync(refresh_download=True)


@router.post("/simulation-build-preview", response_model=SimulationBuildPreviewRead)
def preview_simulation_build(
    request: SimulationBuildPreviewRequest,
    session: Session = Depends(get_db_session),
) -> SimulationBuildPreviewRead:
    service = UnitBuildService(session)
    try:
        preview = service.preview_attacker_build(
            request.attacker_datasheet_id,
            request.attacker_leader_ids,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return SimulationBuildPreviewRead(
        attacker_id=preview.attacker.id,
        attacker_name=preview.attacker.name,
        selected_leaders=[
            {
                "id": leader.id,
                "name": leader.name,
                "faction_name": leader.faction_name,
                "role": leader.role,
            }
            for leader in preview.selected_leaders
        ],
        effects=[
            {
                "id": effect.id,
                "source_datasheet_id": effect.source.id,
                "source_name": effect.source.name,
                "ability_name": effect.ability_name,
                "summary": effect.summary,
                "effect_type": effect.effect_type,
                "scope": effect.scope,
                "selectable": effect.selectable,
                "enabled_by_default": effect.enabled_by_default,
            }
            for effect in preview.effects
        ],
        unmodeled_abilities=list(preview.unmodeled_abilities),
    )


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
