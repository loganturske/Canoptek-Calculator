from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..domain.simulation import DiceExpression
from ..domain.unit_build import (
    SIMULATION_EFFECT_TYPES,
    AttackScope,
    DatasheetReference,
    UnitBuildEffect,
    ability_looks_simulation_relevant,
    build_effect_id,
    interpret_ability_effects,
    normalize_rules_text,
)
from ..models import (
    Ability,
    Datasheet,
    DatasheetAbility,
    DatasheetAbilityInterpretation,
    DatasheetStructuredEffect,
    Faction,
)

_VARIANT_KEY_PATTERN = re.compile(r"[^a-z0-9]+")
_SUPPORTED_WOUND_REROLLS = {"ones", "fails"}
_OPENAI_INTERPRETER_KIND = "openai"
_HEURISTIC_INTERPRETER_KIND = "heuristic"
_SIMULATION_SCOPE_VALUES = {"any", "ranged", "melee"}
_SYSTEM_PROMPT = (
    "You translate Warhammer 40,000 datasheet abilities into a narrow combat-effect DSL "
    "for a deterministic simulator.\n\n"
    "Only return effects that directly change the attacking unit's own hit rolls, wound "
    "rolls, critical-hit threshold, Lethal Hits, or Sustained Hits during the attack "
    "sequence. Ignore movement, command phase healing, mortal-wound side effects, "
    "enemy-only debuffs, aura ranges, defensive durability, and anything that cannot be "
    "represented by the schema.\n\n"
    "Set enabled_by_default to true when the effect is automatically active as soon as "
    "this datasheet is part of the attacking unit. Set enabled_by_default to false when "
    "the effect depends on a battle-state condition the UI should let the user toggle "
    "on.\n\n"
    "Allowed effect types:\n"
    "- hit_crit_threshold: numeric_value 2-6\n"
    "- hit_modifier: numeric_value integer\n"
    "- wound_modifier: numeric_value integer\n"
    '- wound_reroll: text_value "ones" or "fails"\n'
    "- grant_lethal_hits\n"
    '- grant_sustained_hits: text_value like "1", "2", "D3", or "D6"\n\n'
    "Allowed scopes: any, ranged, melee.\n\n"
    "Return no effects if you are not confident the rule fits this DSL. Do not invent "
    "rules."
)

_BATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["abilities"],
    "properties": {
        "abilities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["datasheet_id", "ability_line", "relevant", "effects"],
                "properties": {
                    "datasheet_id": {"type": "string"},
                    "ability_line": {"type": "integer"},
                    "relevant": {"type": "boolean"},
                    "confidence": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                    "note": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "effects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "variant_key",
                                "summary",
                                "effect_type",
                                "scope",
                                "enabled_by_default",
                            ],
                            "properties": {
                                "variant_key": {"type": "string"},
                                "summary": {"type": "string"},
                                "effect_type": {
                                    "type": "string",
                                    "enum": sorted(SIMULATION_EFFECT_TYPES),
                                },
                                "scope": {
                                    "type": "string",
                                    "enum": sorted(_SIMULATION_SCOPE_VALUES),
                                },
                                "numeric_value": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                                "text_value": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                                "enabled_by_default": {"type": "boolean"},
                                "confidence": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                            },
                        },
                    },
                },
            },
        }
    },
}


@dataclass(frozen=True)
class AbilitySourceRecord:
    source: DatasheetReference
    ability_line: int
    ability_name: str
    ability_type: str | None
    description: str | None

    @property
    def key(self) -> tuple[str, int]:
        return (self.source.id, self.ability_line)


@dataclass(frozen=True)
class AIInterpretedEffect:
    variant_key: str
    summary: str
    effect_type: str
    scope: AttackScope = "any"
    numeric_value: int | None = None
    text_value: str | None = None
    enabled_by_default: bool = True
    confidence: float | None = None


@dataclass(frozen=True)
class AIAbilityInterpretation:
    relevant: bool
    confidence: float | None = None
    note: str | None = None
    effects: tuple[AIInterpretedEffect, ...] = ()


@dataclass(frozen=True)
class StructuredEffectSyncSummary:
    abilities_scanned: int
    relevant_abilities: int
    interpreted_abilities: int
    effects_persisted: int
    ai_interpreted_abilities: int


class OpenAIAbilityInterpreter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.unit_effect_ai_enabled and self.settings.openai_api_key)

    def interpret(
        self,
        abilities: list[AbilitySourceRecord],
    ) -> dict[tuple[str, int], AIAbilityInterpretation]:
        if not self.configured or not abilities:
            return {}

        interpretations: dict[tuple[str, int], AIAbilityInterpretation] = {}
        for batch in _chunked(abilities, max(self.settings.unit_effect_ai_batch_size, 1)):
            response_map = self._interpret_batch(batch)
            interpretations.update(response_map)
        return interpretations

    def _interpret_batch(
        self,
        abilities: list[AbilitySourceRecord],
    ) -> dict[tuple[str, int], AIAbilityInterpretation]:
        payload = {
            "model": self.settings.unit_effect_ai_model,
            "input": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "abilities": [
                                {
                                    "datasheet_id": ability.source.id,
                                    "datasheet_name": ability.source.name,
                                    "faction_name": ability.source.faction_name,
                                    "role": ability.source.role,
                                    "ability_line": ability.ability_line,
                                    "ability_name": ability.ability_name,
                                    "ability_type": ability.ability_type,
                                    "description": normalize_rules_text(ability.description),
                                }
                                for ability in abilities
                            ]
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "datasheet_ability_effect_batch",
                    "schema": _BATCH_SCHEMA,
                    "strict": True,
                }
            },
        }

        response = httpx.post(
            f"{self.settings.unit_effect_ai_base_url.rstrip('/')}/responses",
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.settings.unit_effect_ai_timeout_seconds,
        )
        response.raise_for_status()

        raw_payload = response.json()
        response_text = _extract_response_text(raw_payload)
        structured = json.loads(response_text)

        interpretations: dict[tuple[str, int], AIAbilityInterpretation] = {}
        for ability_payload in structured.get("abilities", []):
            datasheet_id = str(ability_payload.get("datasheet_id") or "").strip()
            ability_line = ability_payload.get("ability_line")
            if not datasheet_id or not isinstance(ability_line, int):
                continue

            effects = tuple(
                effect
                for effect in (
                    _parse_ai_effect(effect_payload)
                    for effect_payload in ability_payload.get("effects", [])
                )
                if effect is not None
            )
            interpretations[(datasheet_id, ability_line)] = AIAbilityInterpretation(
                relevant=bool(ability_payload.get("relevant", False)),
                confidence=_coerce_confidence(ability_payload.get("confidence")),
                note=_coerce_text(ability_payload.get("note")),
                effects=effects,
            )

        return interpretations


class AbilityInterpretationService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.ai_interpreter = OpenAIAbilityInterpreter(self.settings)

    def refresh(self) -> StructuredEffectSyncSummary:
        self.session.execute(delete(DatasheetStructuredEffect))
        self.session.execute(delete(DatasheetAbilityInterpretation))

        ability_sources = self._load_ability_sources()
        ai_candidates = [
            ability
            for ability in ability_sources
            if ability_looks_simulation_relevant(ability.description)
        ]
        ai_results: dict[tuple[str, int], AIAbilityInterpretation] = {}
        try:
            ai_results = self.ai_interpreter.interpret(ai_candidates)
        except Exception:
            ai_results = {}

        interpretation_rows: list[dict[str, object]] = []
        effect_rows: list[dict[str, object]] = []
        relevant_abilities = 0
        interpreted_abilities = 0
        ai_interpreted_abilities = 0

        for ability in ability_sources:
            heuristic_effects = interpret_ability_effects(
                ability.source,
                ability.ability_name,
                ability.description,
            )
            looks_relevant = ability_looks_simulation_relevant(ability.description)
            ai_result = ai_results.get(ability.key)
            chosen_effects, interpreter_kind, confidence, note = self._resolve_effects(
                ability,
                heuristic_effects,
                looks_relevant,
                ai_result,
            )

            if looks_relevant or bool(chosen_effects):
                relevant_abilities += 1
            if chosen_effects:
                interpreted_abilities += 1
            if interpreter_kind == _OPENAI_INTERPRETER_KIND and chosen_effects:
                ai_interpreted_abilities += 1

            interpretation_rows.append(
                {
                    "datasheet_id": ability.source.id,
                    "ability_line": ability.ability_line,
                    "ability_name": ability.ability_name,
                    "ability_type": ability.ability_type,
                    "is_simulation_relevant": looks_relevant or bool(chosen_effects),
                    "interpreted": bool(chosen_effects),
                    "interpreter_kind": interpreter_kind,
                    "confidence": confidence,
                    "note": note,
                }
            )

            for effect in chosen_effects:
                effect_rows.append(
                    {
                        "datasheet_id": ability.source.id,
                        "ability_line": ability.ability_line,
                        "ability_name": ability.ability_name,
                        "effect_id": effect.id,
                        "summary": effect.summary,
                        "effect_type": effect.effect_type,
                        "scope": effect.scope,
                        "numeric_value": effect.numeric_value,
                        "text_value": effect.text_value,
                        "selectable": effect.selectable,
                        "enabled_by_default": effect.enabled_by_default,
                        "interpreter_kind": interpreter_kind,
                        "confidence": confidence,
                    }
                )

        if interpretation_rows:
            self.session.execute(insert(DatasheetAbilityInterpretation), interpretation_rows)
        if effect_rows:
            self.session.execute(insert(DatasheetStructuredEffect), effect_rows)

        return StructuredEffectSyncSummary(
            abilities_scanned=len(ability_sources),
            relevant_abilities=relevant_abilities,
            interpreted_abilities=interpreted_abilities,
            effects_persisted=len(effect_rows),
            ai_interpreted_abilities=ai_interpreted_abilities,
        )

    def _resolve_effects(
        self,
        ability: AbilitySourceRecord,
        heuristic_effects: tuple[UnitBuildEffect, ...],
        looks_relevant: bool,
        ai_result: AIAbilityInterpretation | None,
    ) -> tuple[tuple[UnitBuildEffect, ...], str | None, float | None, str | None]:
        if ai_result is not None and ai_result.effects:
            return (
                _dedupe_effects(
                    tuple(
                        _build_effect_from_ai(ability.source, ability.ability_name, effect)
                        for effect in ai_result.effects
                    )
                ),
                _OPENAI_INTERPRETER_KIND,
                ai_result.confidence,
                ai_result.note,
            )

        if heuristic_effects:
            return heuristic_effects, _HEURISTIC_INTERPRETER_KIND, None, None

        if ai_result is not None and ai_result.relevant:
            return (
                (),
                _OPENAI_INTERPRETER_KIND,
                ai_result.confidence,
                (
                    ai_result.note
                    or "Relevant attack rule does not map cleanly to the current effect DSL."
                ),
            )

        if looks_relevant:
            return (
                (),
                None,
                None,
                "Relevant attack rule does not map cleanly to the current effect DSL.",
            )

        return (), None, None, None

    def _load_ability_sources(self) -> list[AbilitySourceRecord]:
        rows = self.session.execute(
            select(
                Datasheet.id,
                Datasheet.name,
                Faction.name,
                Datasheet.role,
                DatasheetAbility.line,
                DatasheetAbility.name,
                DatasheetAbility.description,
                DatasheetAbility.type,
                Ability.name,
                Ability.description,
            )
            .join(Datasheet, DatasheetAbility.datasheet_id == Datasheet.id)
            .join(Faction, Datasheet.faction_id == Faction.id)
            .outerjoin(Ability, DatasheetAbility.ability_id == Ability.id)
            .order_by(Datasheet.name.asc(), DatasheetAbility.line.asc())
        ).all()

        ability_sources: list[AbilitySourceRecord] = []
        for (
            datasheet_id,
            datasheet_name,
            faction_name,
            role,
            ability_line,
            ability_name,
            ability_description,
            ability_type,
            inherited_name,
            inherited_description,
        ) in rows:
            ability_sources.append(
                AbilitySourceRecord(
                    source=DatasheetReference(
                        id=datasheet_id,
                        name=datasheet_name,
                        faction_name=faction_name,
                        role=role,
                    ),
                    ability_line=ability_line,
                    ability_name=ability_name or inherited_name or "Unnamed ability",
                    ability_type=ability_type,
                    description=ability_description or inherited_description,
                )
            )

        return ability_sources


def _build_effect_from_ai(
    source: DatasheetReference,
    ability_name: str,
    effect: AIInterpretedEffect,
) -> UnitBuildEffect:
    variant_key = _normalize_variant_key(effect.variant_key)
    return UnitBuildEffect(
        id=build_effect_id(source.id, ability_name, variant_key),
        source=source,
        ability_name=ability_name,
        summary=effect.summary,
        effect_type=effect.effect_type,
        scope=effect.scope,
        numeric_value=effect.numeric_value,
        text_value=effect.text_value,
        selectable=True,
        enabled_by_default=effect.enabled_by_default,
    )


def _chunked(values: list[AbilitySourceRecord], size: int) -> list[list[AbilitySourceRecord]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _coerce_confidence(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if 0.0 <= numeric <= 1.0 else None
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _extract_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return str(content.get("text") or "")
            if content.get("type") == "refusal":
                raise ValueError(
                    content.get("refusal") or "The model refused the interpretation request."
                )

    raise ValueError("OpenAI did not return structured output text.")


def _normalize_variant_key(value: str | None) -> str:
    normalized = _VARIANT_KEY_PATTERN.sub("-", (value or "").strip().lower()).strip("-")
    return normalized[:64] or "effect"


def _parse_ai_effect(payload: dict[str, Any]) -> AIInterpretedEffect | None:
    effect_type = str(payload.get("effect_type") or "").strip()
    if effect_type not in SIMULATION_EFFECT_TYPES:
        return None

    scope = str(payload.get("scope") or "any").strip().lower()
    if scope not in _SIMULATION_SCOPE_VALUES:
        scope = "any"

    summary = _coerce_text(payload.get("summary"))
    if summary is None:
        return None

    numeric_value = payload.get("numeric_value")
    if not isinstance(numeric_value, int):
        numeric_value = None

    text_value = _coerce_text(payload.get("text_value"))
    enabled_by_default = bool(payload.get("enabled_by_default", True))

    if effect_type == "hit_crit_threshold":
        if numeric_value is None or not 2 <= numeric_value <= 6:
            return None
    elif effect_type in {"hit_modifier", "wound_modifier"}:
        if numeric_value is None:
            return None
    elif effect_type == "wound_reroll":
        if text_value not in _SUPPORTED_WOUND_REROLLS:
            return None
    elif effect_type == "grant_sustained_hits":
        if text_value is None or DiceExpression.parse(text_value.upper()) is None:
            return None
        text_value = text_value.upper()

    return AIInterpretedEffect(
        variant_key=_normalize_variant_key(str(payload.get("variant_key") or "")),
        summary=summary,
        effect_type=effect_type,
        scope=scope,  # type: ignore[arg-type]
        numeric_value=numeric_value,
        text_value=text_value,
        enabled_by_default=enabled_by_default,
        confidence=_coerce_confidence(payload.get("confidence")),
    )


def _dedupe_effects(effects: tuple[UnitBuildEffect, ...]) -> tuple[UnitBuildEffect, ...]:
    deduped: dict[str, UnitBuildEffect] = {}
    for effect in effects:
        deduped.setdefault(effect.id, effect)
    return tuple(deduped.values())
