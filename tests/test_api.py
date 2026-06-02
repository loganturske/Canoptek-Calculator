from __future__ import annotations

from fastapi.testclient import TestClient

from canoptek_calculator.ingest.service import DataImportService
from canoptek_calculator.main import create_app


def test_api_exposes_datasheets_and_simulation(isolated_environment) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    app = create_app()
    with TestClient(app) as client:
        datasheets = client.get("/api/datasheets")
        assert datasheets.status_code == 200
        assert len(datasheets.json()) == 2

        detail = client.get("/api/datasheets/000000600")
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["name"] == "Necron Warriors"
        assert payload["weapons"][0]["name"] == "Gauss flayer"

        simulation = client.post(
            "/api/simulate",
            json={
                "attacker_weapon_id": 1,
                "attacker_models": 10,
                "defender_mode": "datasheet",
                "defender_model_id": 2,
                "target_model_count": 5,
                "half_range": True,
                "trials": 500,
                "seed": 99,
            },
        )
        assert simulation.status_code == 200
        simulation_payload = simulation.json()
        assert simulation_payload["weapon_name"] == "Gauss flayer"
        assert simulation_payload["monte_carlo"]["average_wounds_lost"] > 0


def test_trusted_host_middleware_rejects_unexpected_hosts(isolated_environment) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"host": "evil.example.com"})
        assert response.status_code == 400


def test_homepage_includes_static_assets_and_error_popup(
    isolated_environment,
) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert 'href="/static/css/app.css"' in response.text
        assert 'src="/static/js/app.js"' in response.text
        assert 'id="error-popup"' in response.text
        assert 'id="error-popup-retry"' in response.text
