from __future__ import annotations

from sqlalchemy import select

from canoptek_calculator.db import get_session_factory
from canoptek_calculator.ingest.service import DataImportService
from canoptek_calculator.models import DatasheetModel, DatasheetWargear
from canoptek_calculator.schemas.api import SimulationRequest
from canoptek_calculator.services.simulation import SimulationService
from canoptek_calculator.services.unit_builds import UnitBuildService


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


def test_unit_build_effects_apply_to_simulation(isolated_environment) -> None:
    service = DataImportService.from_defaults()
    service.import_fixtures(isolated_environment)

    with get_session_factory()() as session:
        simulation_service = SimulationService(session)
        unit_build_service = UnitBuildService(session)
        immortals_weapon_id = session.scalar(
            select(DatasheetWargear.row_id).where(
                DatasheetWargear.datasheet_id == "000000535",
                DatasheetWargear.name == "Gauss blaster",
            )
        )
        intercessor_model_id = session.scalar(
            select(DatasheetModel.row_id).where(DatasheetModel.datasheet_id == "000000601")
        )
        preview = unit_build_service.preview_attacker_build(
            "000000535",
            ["000002108"],
        )
        default_effect_ids = [effect.id for effect in preview.effects if effect.enabled_by_default]
        target_on_objective_effect = next(
            effect.id for effect in preview.effects if not effect.enabled_by_default
        )

        base_response = simulation_service.simulate(
            SimulationRequest(
                attacker_weapon_id=immortals_weapon_id,
                attacker_models=10,
                defender_mode="datasheet",
                defender_model_id=intercessor_model_id,
                target_model_count=5,
                trials=1000,
                seed=17,
            )
        )
        leader_response = simulation_service.simulate(
            SimulationRequest(
                attacker_weapon_id=immortals_weapon_id,
                attacker_models=10,
                attacker_leader_ids=["000002108"],
                defender_mode="datasheet",
                defender_model_id=intercessor_model_id,
                target_model_count=5,
                trials=1000,
                seed=17,
            )
        )
        explicit_default_response = simulation_service.simulate(
            SimulationRequest(
                attacker_weapon_id=immortals_weapon_id,
                attacker_models=10,
                attacker_leader_ids=["000002108"],
                attacker_enabled_effect_ids=default_effect_ids,
                defender_mode="datasheet",
                defender_model_id=intercessor_model_id,
                target_model_count=5,
                trials=1000,
                seed=17,
            )
        )
        objective_response = simulation_service.simulate(
            SimulationRequest(
                attacker_weapon_id=immortals_weapon_id,
                attacker_models=10,
                attacker_enabled_effect_ids=[target_on_objective_effect],
                defender_mode="datasheet",
                defender_model_id=intercessor_model_id,
                target_model_count=5,
                trials=1000,
                seed=17,
            )
        )
        disabled_response = simulation_service.simulate(
            SimulationRequest(
                attacker_weapon_id=immortals_weapon_id,
                attacker_models=10,
                attacker_leader_ids=["000002108"],
                attacker_enabled_effect_ids=[],
                defender_mode="datasheet",
                defender_model_id=intercessor_model_id,
                target_model_count=5,
                trials=1000,
                seed=17,
            )
        )

    assert base_response.expected.wounds > 0
    assert leader_response.expected.wounds > base_response.expected.wounds
    assert explicit_default_response.expected.wounds == leader_response.expected.wounds
    assert leader_response.attacker_leaders == ["Plasmancer"]
    assert any("Harbinger of Destruction" in effect for effect in leader_response.applied_effects)
    assert objective_response.expected.wounds > base_response.expected.wounds
    assert disabled_response.expected.wounds < base_response.expected.wounds
    assert disabled_response.applied_effects == []
