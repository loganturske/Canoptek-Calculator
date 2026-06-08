from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..domain.unit_build import (
    DatasheetReference,
    ResolvedAttackModifiers,
    UnitBuildEffect,
    resolve_attack_modifiers,
)
from ..models import (
    Datasheet,
    DatasheetAbilityInterpretation,
    DatasheetLeader,
    DatasheetStructuredEffect,
    Faction,
)


@dataclass(frozen=True)
class AttackerBuildPreview:
    attacker: DatasheetReference
    selected_leaders: tuple[DatasheetReference, ...]
    attachable_leaders: tuple[DatasheetReference, ...]
    effects: tuple[UnitBuildEffect, ...]
    unmodeled_abilities: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedAttackerBuild:
    preview: AttackerBuildPreview
    modifiers: ResolvedAttackModifiers


class UnitBuildService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def preview_attacker_build(
        self,
        attacker_datasheet_id: str,
        attacker_leader_ids: list[str] | tuple[str, ...] = (),
    ) -> AttackerBuildPreview:
        attacker = self._load_datasheet_reference(attacker_datasheet_id)
        attachable_leaders = self.list_attachable_leaders(attacker_datasheet_id)
        self._validate_attached_leaders(
            attacker_name=attacker.name,
            allowed_leaders=attachable_leaders,
            selected_leader_ids=attacker_leader_ids,
        )
        selected_leaders = tuple(
            self._load_datasheet_reference(leader_id) for leader_id in attacker_leader_ids
        )

        effects: list[UnitBuildEffect] = []
        unmodeled_abilities: list[str] = []
        for source in (attacker, *selected_leaders):
            effects.extend(self._load_structured_effects(source))
            unmodeled_abilities.extend(self._load_unmodeled_abilities(source))

        deduped_effect_map: dict[str, UnitBuildEffect] = {}
        for effect in effects:
            deduped_effect_map.setdefault(effect.id, effect)

        return AttackerBuildPreview(
            attacker=attacker,
            selected_leaders=selected_leaders,
            attachable_leaders=attachable_leaders,
            effects=tuple(deduped_effect_map.values()),
            unmodeled_abilities=tuple(dict.fromkeys(unmodeled_abilities)),
        )

    def resolve_attacker_build(
        self,
        attacker_datasheet_id: str,
        *,
        attacker_leader_ids: list[str] | tuple[str, ...] = (),
        attacker_enabled_effect_ids: list[str] | tuple[str, ...] | None = None,
        weapon_kind: str | None,
    ) -> ResolvedAttackerBuild:
        preview = self.preview_attacker_build(attacker_datasheet_id, attacker_leader_ids)
        available_effect_ids = {effect.id for effect in preview.effects if effect.selectable}
        if attacker_enabled_effect_ids is not None:
            for effect_id in attacker_enabled_effect_ids:
                if effect_id not in available_effect_ids:
                    raise ValueError(
                        "The simulation effect "
                        f"{effect_id} is not available for {preview.attacker.name}."
                    )

        modifiers = resolve_attack_modifiers(
            preview.effects,
            weapon_kind=weapon_kind,
            enabled_effect_ids=attacker_enabled_effect_ids,
        )
        return ResolvedAttackerBuild(preview=preview, modifiers=modifiers)

    def list_attachable_leaders(self, datasheet_id: str) -> tuple[DatasheetReference, ...]:
        rows = self.session.execute(
            select(Datasheet.id, Datasheet.name, Faction.name, Datasheet.role)
            .join(DatasheetLeader, Datasheet.id == DatasheetLeader.leader_id)
            .join(Faction, Datasheet.faction_id == Faction.id)
            .where(DatasheetLeader.attached_id == datasheet_id)
            .order_by(Datasheet.name.asc())
        ).all()
        return tuple(
            DatasheetReference(
                id=row[0],
                name=row[1],
                faction_name=row[2],
                role=row[3],
            )
            for row in rows
        )

    def _load_datasheet_reference(self, datasheet_id: str) -> DatasheetReference:
        row = self.session.execute(
            select(Datasheet.id, Datasheet.name, Faction.name, Datasheet.role)
            .join(Faction, Datasheet.faction_id == Faction.id)
            .where(Datasheet.id == datasheet_id)
        ).one_or_none()
        if row is None:
            raise LookupError(f"Datasheet {datasheet_id} was not found.")

        return DatasheetReference(
            id=row[0],
            name=row[1],
            faction_name=row[2],
            role=row[3],
        )

    def _load_structured_effects(self, source: DatasheetReference) -> list[UnitBuildEffect]:
        rows = self.session.scalars(
            select(DatasheetStructuredEffect)
            .where(DatasheetStructuredEffect.datasheet_id == source.id)
            .order_by(
                DatasheetStructuredEffect.ability_line.asc(),
                DatasheetStructuredEffect.row_id.asc(),
            )
        ).all()
        return [
            UnitBuildEffect(
                id=row.effect_id,
                source=source,
                ability_name=row.ability_name,
                summary=row.summary,
                effect_type=row.effect_type,  # type: ignore[arg-type]
                scope=row.scope,  # type: ignore[arg-type]
                numeric_value=row.numeric_value,
                text_value=row.text_value,
                selectable=row.selectable,
                enabled_by_default=row.enabled_by_default,
            )
            for row in rows
        ]

    def _load_unmodeled_abilities(self, source: DatasheetReference) -> list[str]:
        ability_names = self.session.scalars(
            select(DatasheetAbilityInterpretation.ability_name)
            .where(DatasheetAbilityInterpretation.datasheet_id == source.id)
            .where(DatasheetAbilityInterpretation.is_simulation_relevant.is_(True))
            .where(DatasheetAbilityInterpretation.interpreted.is_(False))
            .where(
                or_(
                    DatasheetAbilityInterpretation.ability_type.not_in(("Core", "Faction")),
                    DatasheetAbilityInterpretation.ability_type.is_(None),
                )
            )
            .order_by(DatasheetAbilityInterpretation.ability_line.asc())
        ).all()
        return [f"{source.name} - {ability_name}" for ability_name in ability_names]

    def _validate_attached_leaders(
        self,
        *,
        attacker_name: str,
        allowed_leaders: tuple[DatasheetReference, ...],
        selected_leader_ids: list[str] | tuple[str, ...],
    ) -> None:
        allowed_ids = {leader.id for leader in allowed_leaders}
        for leader_id in selected_leader_ids:
            if leader_id not in allowed_ids:
                raise ValueError(
                    f"The selected leader {leader_id} cannot be attached to {attacker_name}."
                )
