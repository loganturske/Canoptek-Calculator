from __future__ import annotations

from canoptek_calculator.db import get_session_factory
from canoptek_calculator.ingest.service import DataImportService
from canoptek_calculator.schemas.api import SimulationRequest
from canoptek_calculator.services.simulation import SimulationService


def test_simulation_service_returns_damage_profile(isolated_environment) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    with get_session_factory()() as session:
        simulation_service = SimulationService(session)
        response = simulation_service.simulate(
            SimulationRequest(
                attacker_weapon_id=1,
                attacker_models=10,
                defender_mode="datasheet",
                defender_model_id=2,
                target_model_count=5,
                half_range=True,
                trials=1000,
                seed=7,
            )
        )

    assert response.weapon_name == "Gauss flayer"
    assert response.target_name == "Intercessor"
    assert response.expected.attacks > 10
    assert response.expected.hits > 0
    assert response.monte_carlo.average_wounds_lost > 0
    assert "rapid fire 1" in response.supported_rules
    assert "lethal hits" in response.supported_rules
