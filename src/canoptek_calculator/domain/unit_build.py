from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Literal

from .simulation import DiceExpression, RerollMode

AttackScope = Literal["any", "ranged", "melee"]
SimulationEffectType = Literal[
    "grant_lethal_hits",
    "grant_sustained_hits",
    "hit_crit_threshold",
    "hit_modifier",
    "wound_modifier",
    "wound_reroll",
]

_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_CRITICAL_HIT_PATTERN = re.compile(
    r"(?:critical hit is scored on|(?:a |an )?(?:successful )?unmodif\w* hit roll of)\s+([2-6])\+",
    flags=re.IGNORECASE,
)
_SUSTAINED_HITS_PATTERN = re.compile(
    r"weapons equipped by models in (?:that|this) unit have the "
    r"\[sustained hits ([^\]]+)\] ability",
    flags=re.IGNORECASE,
)

_SIMULATION_KEYWORDS = (
    "attack",
    "attacks",
    "critical hit",
    "damage",
    "fight phase",
    "hit roll",
    "mortal wound",
    "save",
    "shoot",
    "shooting phase",
    "weapon",
    "wound roll",
)
SIMULATION_EFFECT_TYPES = frozenset(
    {
        "grant_lethal_hits",
        "grant_sustained_hits",
        "hit_crit_threshold",
        "hit_modifier",
        "wound_modifier",
        "wound_reroll",
    }
)


@dataclass(frozen=True)
class DatasheetReference:
    id: str
    name: str
    faction_name: str
    role: str | None = None


@dataclass(frozen=True)
class UnitBuildEffect:
    id: str
    source: DatasheetReference
    ability_name: str
    summary: str
    effect_type: SimulationEffectType
    scope: AttackScope = "any"
    numeric_value: int | None = None
    text_value: str | None = None
    selectable: bool = True
    enabled_by_default: bool = True


@dataclass(frozen=True)
class ResolvedAttackModifiers:
    hit_crit_threshold: int = 6
    bonus_hit_modifier: int = 0
    bonus_wound_modifier: int = 0
    granted_wound_reroll: RerollMode | None = None
    granted_lethal_hits: bool = False
    granted_sustained_hits: DiceExpression | None = None
    applied_effects: tuple[str, ...] = ()


def normalize_rules_text(value: str | None) -> str:
    if not value:
        return ""

    without_tags = _HTML_TAG_PATTERN.sub(" ", value)
    unescaped = html.unescape(without_tags)
    return _WHITESPACE_PATTERN.sub(" ", unescaped).strip()


def ability_looks_simulation_relevant(value: str | None) -> bool:
    normalized = normalize_rules_text(value).lower()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in _SIMULATION_KEYWORDS)


def interpret_ability_effects(
    source: DatasheetReference,
    ability_name: str,
    description: str | None,
) -> tuple[UnitBuildEffect, ...]:
    normalized = normalize_rules_text(description)
    if not normalized:
        return ()

    lowered = normalized.lower()
    scope = detect_attack_scope(lowered)
    effects: list[UnitBuildEffect] = []

    if "re-roll a wound roll of 1" in lowered or "reroll a wound roll of 1" in lowered:
        effects.append(
            UnitBuildEffect(
                id=_build_effect_id(source.id, ability_name, "wound-reroll-ones"),
                source=source,
                ability_name=ability_name,
                summary=f"{_scope_prefix(scope)}re-roll wound rolls of 1.",
                effect_type="wound_reroll",
                scope=scope,
                text_value="ones",
                selectable=True,
            )
        )

    if "within range of an objective marker" in lowered and (
        "re-roll the wound roll instead" in lowered or "reroll the wound roll instead" in lowered
    ):
        effects.append(
            UnitBuildEffect(
                id=_build_effect_id(source.id, ability_name, "target-on-objective"),
                source=source,
                ability_name=ability_name,
                summary=(
                    "Target is within range of an objective marker: upgrade wound re-rolls to full."
                ),
                effect_type="wound_reroll",
                scope=scope,
                text_value="fails",
                selectable=True,
                enabled_by_default=False,
            )
        )

    critical_match = _CRITICAL_HIT_PATTERN.search(lowered)
    if critical_match:
        threshold = int(critical_match.group(1))
        effects.append(
            UnitBuildEffect(
                id=_build_effect_id(source.id, ability_name, f"crit-{threshold}"),
                source=source,
                ability_name=ability_name,
                summary=f"{_scope_prefix(scope)}score Critical Hits on {threshold}+.",
                effect_type="hit_crit_threshold",
                scope=scope,
                numeric_value=threshold,
                selectable=True,
            )
        )

    if "add 1 to the hit roll" in lowered:
        effects.append(
            UnitBuildEffect(
                id=_build_effect_id(source.id, ability_name, "hit-plus-1"),
                source=source,
                ability_name=ability_name,
                summary=f"{_scope_prefix(scope)}add 1 to hit rolls.",
                effect_type="hit_modifier",
                scope=scope,
                numeric_value=1,
                selectable=True,
            )
        )

    if "add 1 to the wound roll" in lowered:
        effects.append(
            UnitBuildEffect(
                id=_build_effect_id(source.id, ability_name, "wound-plus-1"),
                source=source,
                ability_name=ability_name,
                summary=f"{_scope_prefix(scope)}add 1 to wound rolls.",
                effect_type="wound_modifier",
                scope=scope,
                numeric_value=1,
                selectable=True,
            )
        )

    if re.search(
        r"weapons equipped by models in (?:that|this) unit have the \[lethal hits\] ability",
        lowered,
    ):
        effects.append(
            UnitBuildEffect(
                id=_build_effect_id(source.id, ability_name, "lethal-hits"),
                source=source,
                ability_name=ability_name,
                summary=f"{_scope_prefix(scope)}gain Lethal Hits.",
                effect_type="grant_lethal_hits",
                scope=scope,
                selectable=True,
            )
        )

    sustained_match = _SUSTAINED_HITS_PATTERN.search(lowered)
    if sustained_match:
        sustained_value = sustained_match.group(1).strip().upper()
        if DiceExpression.parse(sustained_value):
            effects.append(
                UnitBuildEffect(
                    id=_build_effect_id(source.id, ability_name, "sustained-hits"),
                    source=source,
                    ability_name=ability_name,
                    summary=f"{_scope_prefix(scope)}gain Sustained Hits {sustained_value}.",
                    effect_type="grant_sustained_hits",
                    scope=scope,
                    text_value=sustained_value,
                    selectable=True,
                )
            )

    return tuple(effects)


def resolve_attack_modifiers(
    effects: list[UnitBuildEffect] | tuple[UnitBuildEffect, ...],
    *,
    weapon_kind: str | None,
    enabled_effect_ids: list[str] | tuple[str, ...] | None,
) -> ResolvedAttackModifiers:
    hit_crit_threshold = 6
    bonus_hit_modifier = 0
    bonus_wound_modifier = 0
    granted_wound_reroll: RerollMode | None = None
    granted_lethal_hits = False
    granted_sustained_hits: DiceExpression | None = None
    applied_effects: list[str] = []
    enabled_ids = (
        set(enabled_effect_ids)
        if enabled_effect_ids is not None
        else {effect.id for effect in effects if effect.enabled_by_default or not effect.selectable}
    )

    for effect in effects:
        if effect.id not in enabled_ids:
            continue
        if not _scope_matches_weapon(effect.scope, weapon_kind):
            continue

        if effect.effect_type == "hit_crit_threshold" and effect.numeric_value is not None:
            hit_crit_threshold = min(hit_crit_threshold, effect.numeric_value)
        elif effect.effect_type == "hit_modifier" and effect.numeric_value is not None:
            bonus_hit_modifier += effect.numeric_value
        elif effect.effect_type == "wound_modifier" and effect.numeric_value is not None:
            bonus_wound_modifier += effect.numeric_value
        elif effect.effect_type == "wound_reroll" and effect.text_value is not None:
            granted_wound_reroll = _stronger_reroll(granted_wound_reroll, effect.text_value)
        elif effect.effect_type == "grant_lethal_hits":
            granted_lethal_hits = True
        elif effect.effect_type == "grant_sustained_hits" and effect.text_value:
            candidate = DiceExpression.parse(effect.text_value)
            if candidate:
                granted_sustained_hits = _prefer_higher_expression(
                    granted_sustained_hits,
                    candidate,
                )

        applied_effects.append(f"{effect.source.name} - {effect.ability_name}: {effect.summary}")

    return ResolvedAttackModifiers(
        hit_crit_threshold=hit_crit_threshold,
        bonus_hit_modifier=bonus_hit_modifier,
        bonus_wound_modifier=bonus_wound_modifier,
        granted_wound_reroll=granted_wound_reroll,
        granted_lethal_hits=granted_lethal_hits,
        granted_sustained_hits=granted_sustained_hits,
        applied_effects=tuple(dict.fromkeys(applied_effects)),
    )


def detect_attack_scope(value: str) -> AttackScope:
    if "melee attack" in value or "melee attacks" in value or "melee weapon" in value:
        return "melee"
    if "ranged attack" in value or "ranged attacks" in value or "ranged weapon" in value:
        return "ranged"
    return "any"


def _scope_prefix(scope: AttackScope) -> str:
    if scope == "ranged":
        return "Ranged attacks "
    if scope == "melee":
        return "Melee attacks "
    return "Models in the unit "


def _build_effect_id(source_id: str, ability_name: str, suffix: str) -> str:
    slug = _SLUG_PATTERN.sub("-", ability_name.lower()).strip("-")
    return f"{source_id}:{slug}:{suffix}"


def build_effect_id(source_id: str, ability_name: str, suffix: str) -> str:
    return _build_effect_id(source_id, ability_name, suffix)


def _scope_matches_weapon(scope: AttackScope, weapon_kind: str | None) -> bool:
    if scope == "any":
        return True

    kind = (weapon_kind or "").strip().lower()
    if scope == "ranged":
        return kind == "ranged"
    if scope == "melee":
        return kind == "melee"
    return True


def _prefer_higher_expression(
    current: DiceExpression | None,
    candidate: DiceExpression,
) -> DiceExpression:
    if current is None:
        return candidate
    return candidate if candidate.mean() > current.mean() else current


def _stronger_reroll(
    current: RerollMode | None,
    candidate: str,
) -> RerollMode:
    normalized = candidate.lower()
    next_mode: RerollMode = "fails" if normalized == "fails" else "ones"
    if current == "fails" or next_mode == "fails":
        return "fails"
    return "ones"
