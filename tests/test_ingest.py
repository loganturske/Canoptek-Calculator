from __future__ import annotations

from sqlalchemy import func, select

from canoptek_calculator.db import get_session_factory
from canoptek_calculator.ingest.service import DataImportService
from canoptek_calculator.models import Datasheet, DatasheetWargear, Faction, LastUpdate


def test_import_fixtures_loads_sample_bundle(isolated_environment) -> None:
    service = DataImportService.from_defaults()
    results = service.import_fixtures(isolated_environment)

    rows_by_table = {result.table: result.rows_imported for result in results}
    assert rows_by_table["Factions.csv"] == 2
    assert rows_by_table["Datasheets.csv"] == 2
    assert rows_by_table["Datasheets_wargear.csv"] == 2
    assert rows_by_table["Last_update.csv"] == 1

    with get_session_factory()() as session:
        assert session.scalar(select(func.count()).select_from(Faction)) == 2
        assert session.scalar(select(func.count()).select_from(Datasheet)) == 2
        assert session.scalar(select(func.count()).select_from(DatasheetWargear)) == 2
        assert session.scalar(select(LastUpdate.last_update)) is not None
