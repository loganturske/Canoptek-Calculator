from __future__ import annotations

import csv
from pathlib import Path

from fastapi.testclient import TestClient

from canoptek_calculator.ingest.service import DataImportService
from canoptek_calculator.main import create_app


def rewrite_pipe_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        fieldnames = reader.fieldnames or []

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="|")
        writer.writeheader()
        writer.writerows(rows)


def test_army_list_crud_and_refresh_survival(isolated_environment: Path) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    app = create_app()
    with TestClient(app) as client:
        created = client.post(
            "/api/army-lists",
            json={
                "name": "Silver Tide",
                "faction_id": "NEC",
                "notes": "Awakened Dynasty tournament shell",
            },
        )
        assert created.status_code == 201
        created_payload = created.json()
        list_id = created_payload["id"]

        added_entry = client.post(
            f"/api/army-lists/{list_id}/entries",
            json={
                "datasheet_id": "000000600",
                "model_line": 1,
                "unit_size": 10,
                "quantity": 2,
                "points_each": 100,
                "cost_label": "10 models",
                "nickname": "Warrior Brick",
                "notes": "Objective anchor",
                "sort_order": 20,
            },
        )
        assert added_entry.status_code == 200
        detail = added_entry.json()
        entry_id = detail["entries"][0]["id"]
        assert detail["total_points"] == 200
        assert detail["total_models"] == 20
        assert detail["has_unpriced_entries"] is False
        assert detail["entries"][0]["datasheet_name"] == "Necron Warriors"
        assert detail["entries"][0]["model_profile_id"] is not None

        summaries = client.get("/api/army-lists")
        assert summaries.status_code == 200
        assert summaries.json()[0]["entry_count"] == 1

        updated_list = client.patch(
            f"/api/army-lists/{list_id}",
            json={
                "name": "Silver Tide Prime",
                "notes": "Refined tournament shell",
            },
        )
        assert updated_list.status_code == 200
        assert updated_list.json()["name"] == "Silver Tide Prime"

        updated_entry = client.patch(
            f"/api/army-lists/{list_id}/entries/{entry_id}",
            json={
                "quantity": 1,
                "points_each": 110,
                "nickname": "Frontline Brick",
            },
        )
        assert updated_entry.status_code == 200
        updated_detail = updated_entry.json()
        assert updated_detail["total_points"] == 110
        assert updated_detail["entries"][0]["display_name"] == "Frontline Brick"

        service.import_fixtures(isolated_environment)

        preserved = client.get(f"/api/army-lists/{list_id}")
        assert preserved.status_code == 200
        preserved_payload = preserved.json()
        assert preserved_payload["name"] == "Silver Tide Prime"
        assert preserved_payload["entries"][0]["datasheet_available"] is True
        assert preserved_payload["entries"][0]["model_profile_id"] is not None
        assert preserved_payload["total_points"] == 110

        removed_entry = client.delete(f"/api/army-lists/{list_id}/entries/{entry_id}")
        assert removed_entry.status_code == 200
        assert removed_entry.json()["entry_count"] == 0

        deleted = client.delete(f"/api/army-lists/{list_id}")
        assert deleted.status_code == 204

        missing = client.get(f"/api/army-lists/{list_id}")
        assert missing.status_code == 404


def test_army_list_validation_and_stale_references(isolated_environment: Path) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    app = create_app()
    with TestClient(app) as client:
        missing_faction = client.post(
            "/api/army-lists",
            json={"name": "Ghost List", "faction_id": "MISSING"},
        )
        assert missing_faction.status_code == 404

        created = client.post(
            "/api/army-lists",
            json={"name": "Silver Tide", "faction_id": "NEC"},
        )
        assert created.status_code == 201
        list_id = created.json()["id"]

        wrong_faction = client.post(
            f"/api/army-lists/{list_id}/entries",
            json={
                "datasheet_id": "000000601",
                "unit_size": 5,
                "quantity": 1,
            },
        )
        assert wrong_faction.status_code == 422

        missing_datasheet = client.post(
            f"/api/army-lists/{list_id}/entries",
            json={
                "datasheet_id": "999999999",
                "unit_size": 5,
                "quantity": 1,
            },
        )
        assert missing_datasheet.status_code == 404

        missing_model = client.post(
            f"/api/army-lists/{list_id}/entries",
            json={
                "datasheet_id": "000000600",
                "model_line": 99,
                "unit_size": 10,
                "quantity": 1,
            },
        )
        assert missing_model.status_code == 422

        added_entry = client.post(
            f"/api/army-lists/{list_id}/entries",
            json={
                "datasheet_id": "000000600",
                "model_line": 1,
                "unit_size": 10,
                "quantity": 1,
                "points_each": 100,
            },
        )
        assert added_entry.status_code == 200
        entry_id = added_entry.json()["entries"][0]["id"]

        faction_change = client.patch(
            f"/api/army-lists/{list_id}",
            json={"faction_id": "SM"},
        )
        assert faction_change.status_code == 422

        models_path = isolated_environment / "Datasheets_models.csv"
        with models_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="|")
            rows = list(reader)

        rows[0]["line"] = "2"
        rewrite_pipe_csv(models_path, rows)
        service.import_fixtures(isolated_environment)

        detail = client.get(f"/api/army-lists/{list_id}")
        assert detail.status_code == 200
        payload = detail.json()
        entry = payload["entries"][0]
        assert payload["has_stale_entries"] is True
        assert entry["id"] == entry_id
        assert entry["datasheet_available"] is True
        assert entry["model_available"] is False
        assert "model line" in entry["reference_warning"].lower()

        summary = client.get("/api/army-lists")
        assert summary.status_code == 200
        assert summary.json()[0]["has_stale_entries"] is True
