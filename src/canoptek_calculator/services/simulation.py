from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.simulation import (
    AttackContext,
    CombatSimulator,
    build_target_profile,
    build_weapon_profile,
)
from ..models import Datasheet, DatasheetKeyword, DatasheetModel, DatasheetWargear
from ..schemas.api import (
    HistogramBucketRead,
    SimulationExpectedRead,
    SimulationMonteCarloRead,
    SimulationRequest,
    SimulationResponse,
)


class SimulationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.simulator = CombatSimulator()

    def simulate(self, request: SimulationRequest) -> SimulationResponse:
        weapon_row = self.session.get(DatasheetWargear, request.attacker_weapon_id)
        if weapon_row is None:
            raise LookupError(f"Unable to locate attacker weapon #{request.attacker_weapon_id}.")

        built_weapon = build_weapon_profile(
            weapon_id=weapon_row.row_id,
            name=weapon_row.name,
            kind=weapon_row.type,
            range_value=weapon_row.range,
            attacks_value=weapon_row.a,
            skill_value=weapon_row.bs_ws,
            strength_value=weapon_row.s,
            ap_value=weapon_row.ap,
            damage_value=weapon_row.d,
            description=weapon_row.description,
        )
        if built_weapon.weapon is None:
            raise ValueError(built_weapon.error or "The selected weapon cannot be simulated.")

        target = self._build_target(request)
        context = AttackContext(
            attacker_models=request.attacker_models,
            trials=request.trials,
            hit_reroll=request.hit_reroll,
            wound_reroll=request.wound_reroll,
            hit_modifier=request.hit_modifier,
            wound_modifier=request.wound_modifier,
            half_range=request.half_range,
            stationary=request.stationary,
            charged=request.charged,
            seed=request.seed,
        )
        result = self.simulator.simulate(built_weapon.weapon, target, context)
        return SimulationResponse(
            weapon_name=built_weapon.weapon.name,
            target_name=target.name,
            supported_rules=list(result.supported_rules),
            ignored_rules=list(result.ignored_rules),
            effective_hit_modifier=result.effective_hit_modifier,
            effective_wound_modifier=result.effective_wound_modifier,
            expected=SimulationExpectedRead(
                attacks=result.expected.attacks,
                hits=result.expected.hits,
                wounds=result.expected.wounds,
                unsaved_wounds=result.expected.unsaved_wounds,
                raw_damage=result.expected.raw_damage,
            ),
            monte_carlo=SimulationMonteCarloRead(
                trials=result.monte_carlo.trials,
                average_raw_damage=result.monte_carlo.average_raw_damage,
                average_wounds_lost=result.monte_carlo.average_wounds_lost,
                average_models_slain=result.monte_carlo.average_models_slain,
                kill_probability=result.monte_carlo.kill_probability,
                p10_wounds_lost=result.monte_carlo.p10_wounds_lost,
                median_wounds_lost=result.monte_carlo.median_wounds_lost,
                p90_wounds_lost=result.monte_carlo.p90_wounds_lost,
                histogram=[
                    HistogramBucketRead(
                        wounds_lost=bucket.wounds_lost,
                        occurrences=bucket.occurrences,
                        probability=bucket.probability,
                    )
                    for bucket in result.monte_carlo.histogram
                ],
            ),
        )

    def _build_target(self, request: SimulationRequest):
        if request.defender_mode == "custom":
            return build_target_profile(
                name=request.custom_target_name,
                toughness=request.custom_toughness or 0,
                save=request.custom_save or 7,
                invulnerable_save=request.custom_invulnerable_save,
                wounds_per_model=request.custom_wounds or 1,
                model_count=request.target_model_count,
                keywords=request.custom_keywords,
                in_cover=request.defender_in_cover,
            )

        model_row = self.session.get(DatasheetModel, request.defender_model_id)
        if model_row is None:
            raise LookupError(f"Unable to locate defender model #{request.defender_model_id}.")

        datasheet_name = self.session.scalar(
            select(Datasheet.name).where(Datasheet.id == model_row.datasheet_id)
        )
        keywords = self.session.scalars(
            select(DatasheetKeyword.keyword).where(
                DatasheetKeyword.datasheet_id == model_row.datasheet_id
            )
        ).all()
        return build_target_profile(
            name=model_row.name or datasheet_name or "Unnamed target",
            toughness=model_row.t or "0",
            save=model_row.sv or "7",
            invulnerable_save=model_row.inv_sv,
            wounds_per_model=model_row.w or "1",
            model_count=request.target_model_count,
            keywords=keywords,
            in_cover=request.defender_in_cover,
        )
