from __future__ import annotations

import random
import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal

RerollMode = Literal["none", "ones", "fails"]

_DICE_PATTERN = re.compile(
    r"^\s*(?:(?P<count>\d*)D(?P<sides>\d+)|(?P<fixed>-?\d+))\s*(?:(?P<sign>[+-])\s*(?P<modifier>\d+))?\s*$",
    flags=re.IGNORECASE,
)


def normalize_keyword(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def clamp_modifier(value: int) -> int:
    return max(-1, min(1, value))


def parse_required_roll(value: str | int | None) -> int | None:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    cleaned = value.strip().replace("+", "")
    if cleaned in {"", "-", "N/A"}:
        return None
    return int(cleaned)


def parse_ap(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    cleaned = value.strip()
    if cleaned in {"", "-", "-0", "0"}:
        return 0
    return int(cleaned)


def parse_range_inches(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned in {"", "Melee", "N/A"}:
        return None
    return int(cleaned)


@dataclass(frozen=True)
class DiceExpression:
    original: str
    count: int = 0
    sides: int = 0
    fixed: int | None = None
    modifier: int = 0

    @classmethod
    def parse(cls, value: str | int | None) -> DiceExpression | None:
        if value is None:
            return None

        if isinstance(value, int):
            return cls(original=str(value), fixed=value)

        cleaned = value.strip().upper()
        if cleaned in {"", "-", "N/A"}:
            return None

        match = _DICE_PATTERN.fullmatch(cleaned)
        if not match:
            return None

        fixed = match.group("fixed")
        if fixed is not None:
            base_value = int(fixed)
            modifier = int(match.group("modifier") or 0)
            if match.group("sign") == "-":
                modifier *= -1
            return cls(original=cleaned, fixed=base_value + modifier)

        count = int(match.group("count") or "1")
        sides = int(match.group("sides"))
        modifier = int(match.group("modifier") or 0)
        if match.group("sign") == "-":
            modifier *= -1
        return cls(original=cleaned, count=count, sides=sides, modifier=modifier)

    def mean(self) -> float:
        if self.fixed is not None:
            return float(self.fixed)
        return (self.count * (self.sides + 1) / 2.0) + self.modifier

    def roll(self, rng: random.Random) -> int:
        if self.fixed is not None:
            return self.fixed

        return sum(rng.randint(1, self.sides) for _ in range(self.count)) + self.modifier

    def distribution(self) -> dict[int, float]:
        if self.fixed is not None:
            return {self.fixed: 1.0}

        outcomes: Counter[int] = Counter({0: 1})
        for _ in range(self.count):
            next_outcomes: Counter[int] = Counter()
            for running_total, weight in outcomes.items():
                for face in range(1, self.sides + 1):
                    next_outcomes[running_total + face] += weight
            outcomes = next_outcomes

        total_weight = float(sum(outcomes.values()))
        return {
            total + self.modifier: weight / total_weight
            for total, weight in sorted(outcomes.items())
        }


@dataclass(frozen=True)
class WeaponRules:
    rapid_fire: DiceExpression | None = None
    sustained_hits: DiceExpression | None = None
    lethal_hits: bool = False
    twin_linked: bool = False
    devastating_wounds: bool = False
    torrent: bool = False
    heavy: bool = False
    blast: bool = False
    extra_attacks: bool = False
    melta: DiceExpression | None = None
    lance: bool = False
    ignores_cover: bool = False
    anti_keyword: str | None = None
    anti_threshold: int | None = None
    supported_rules: tuple[str, ...] = ()
    ignored_rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class CombatWeaponProfile:
    weapon_id: int | None
    name: str
    kind: str
    range_inches: int | None
    attacks: DiceExpression
    skill: int | None
    strength: DiceExpression
    ap: int
    damage: DiceExpression
    description: str | None
    rules: WeaponRules


@dataclass(frozen=True)
class WeaponBuildResult:
    weapon: CombatWeaponProfile | None
    rules: WeaponRules
    error: str | None = None


@dataclass(frozen=True)
class TargetProfile:
    name: str
    toughness: int
    save: int
    invulnerable_save: int | None
    wounds_per_model: int
    model_count: int
    keywords: tuple[str, ...]
    in_cover: bool = False


@dataclass(frozen=True)
class AttackContext:
    attacker_models: int
    trials: int
    hit_reroll: RerollMode = "none"
    wound_reroll: RerollMode = "none"
    hit_modifier: int = 0
    wound_modifier: int = 0
    half_range: bool = False
    stationary: bool = False
    charged: bool = False
    seed: int | None = None


@dataclass(frozen=True)
class RollProbabilities:
    success_noncrit: float
    crit: float
    fail: float


@dataclass(frozen=True)
class ExpectedCombatOutcome:
    attacks: float
    hits: float
    wounds: float
    unsaved_wounds: float
    raw_damage: float


@dataclass(frozen=True)
class HistogramBucket:
    wounds_lost: int
    occurrences: int
    probability: float


@dataclass(frozen=True)
class MonteCarloOutcome:
    trials: int
    average_raw_damage: float
    average_wounds_lost: float
    average_models_slain: float
    kill_probability: float
    p10_wounds_lost: float
    median_wounds_lost: float
    p90_wounds_lost: float
    histogram: tuple[HistogramBucket, ...]


@dataclass(frozen=True)
class CombatSimulationResult:
    expected: ExpectedCombatOutcome
    monte_carlo: MonteCarloOutcome
    supported_rules: tuple[str, ...]
    ignored_rules: tuple[str, ...]
    effective_hit_modifier: int
    effective_wound_modifier: int


def parse_weapon_rules(description: str | None) -> WeaponRules:
    if not description:
        return WeaponRules()

    supported_rules: list[str] = []
    ignored_rules: list[str] = []
    rapid_fire: DiceExpression | None = None
    sustained_hits: DiceExpression | None = None
    melta: DiceExpression | None = None
    anti_keyword: str | None = None
    anti_threshold: int | None = None
    lethal_hits = twin_linked = devastating_wounds = False
    torrent = heavy = blast = extra_attacks = False
    lance = ignores_cover = False

    for raw_token in [token.strip() for token in description.split(",") if token.strip()]:
        token = raw_token.lower()
        if token == "lethal hits":
            lethal_hits = True
            supported_rules.append(raw_token)
            continue
        if token == "twin-linked":
            twin_linked = True
            supported_rules.append(raw_token)
            continue
        if token == "devastating wounds":
            devastating_wounds = True
            supported_rules.append(raw_token)
            continue
        if token == "torrent":
            torrent = True
            supported_rules.append(raw_token)
            continue
        if token == "heavy":
            heavy = True
            supported_rules.append(raw_token)
            continue
        if token == "blast":
            blast = True
            supported_rules.append(raw_token)
            continue
        if token == "extra attacks":
            extra_attacks = True
            supported_rules.append(raw_token)
            continue
        if token == "lance":
            lance = True
            supported_rules.append(raw_token)
            continue
        if token == "ignores cover":
            ignores_cover = True
            supported_rules.append(raw_token)
            continue

        if token.startswith("rapid fire "):
            rapid_fire = DiceExpression.parse(token.removeprefix("rapid fire ").strip())
            if rapid_fire:
                supported_rules.append(raw_token)
                continue

        if token.startswith("sustained hits "):
            sustained_hits = DiceExpression.parse(token.removeprefix("sustained hits ").strip())
            if sustained_hits:
                supported_rules.append(raw_token)
                continue

        if token.startswith("melta "):
            melta = DiceExpression.parse(token.removeprefix("melta ").strip())
            if melta:
                supported_rules.append(raw_token)
                continue

        anti_match = re.fullmatch(r"anti-([a-z0-9 \-]+)\s+([2-6])\+?", token)
        if anti_match:
            anti_keyword = anti_match.group(1)
            anti_threshold = int(anti_match.group(2))
            supported_rules.append(raw_token)
            continue

        ignored_rules.append(raw_token)

    return WeaponRules(
        rapid_fire=rapid_fire,
        sustained_hits=sustained_hits,
        lethal_hits=lethal_hits,
        twin_linked=twin_linked,
        devastating_wounds=devastating_wounds,
        torrent=torrent,
        heavy=heavy,
        blast=blast,
        extra_attacks=extra_attacks,
        melta=melta,
        lance=lance,
        ignores_cover=ignores_cover,
        anti_keyword=anti_keyword,
        anti_threshold=anti_threshold,
        supported_rules=tuple(supported_rules),
        ignored_rules=tuple(ignored_rules),
    )


def build_weapon_profile(
    *,
    weapon_id: int | None,
    name: str,
    kind: str | None,
    range_value: str | None,
    attacks_value: str | None,
    skill_value: str | None,
    strength_value: str | None,
    ap_value: str | None,
    damage_value: str | None,
    description: str | None,
) -> WeaponBuildResult:
    rules = parse_weapon_rules(description)
    attacks = DiceExpression.parse(attacks_value)
    strength = DiceExpression.parse(strength_value)
    damage = DiceExpression.parse(damage_value)
    skill = parse_required_roll(skill_value)

    if attacks is None:
        return WeaponBuildResult(None, rules, "The weapon does not have a usable Attacks value.")
    if strength is None:
        return WeaponBuildResult(None, rules, "The weapon does not have a usable Strength value.")
    if damage is None:
        return WeaponBuildResult(None, rules, "The weapon does not have a usable Damage value.")
    if skill is None and not rules.torrent:
        return WeaponBuildResult(
            None,
            rules,
            "The weapon requires a Ballistic Skill or Weapon Skill to simulate.",
        )

    weapon = CombatWeaponProfile(
        weapon_id=weapon_id,
        name=name,
        kind=kind or "Unknown",
        range_inches=parse_range_inches(range_value),
        attacks=attacks,
        skill=skill,
        strength=strength,
        ap=parse_ap(ap_value),
        damage=damage,
        description=description,
        rules=rules,
    )
    return WeaponBuildResult(weapon=weapon, rules=rules, error=None)


def build_target_profile(
    *,
    name: str,
    toughness: str | int,
    save: str | int,
    invulnerable_save: str | int | None,
    wounds_per_model: str | int,
    model_count: int,
    keywords: list[str] | tuple[str, ...],
    in_cover: bool,
) -> TargetProfile:
    parsed_toughness = parse_required_roll(toughness)
    parsed_save = parse_required_roll(save)
    parsed_invulnerable = parse_required_roll(invulnerable_save)
    parsed_wounds = parse_required_roll(wounds_per_model)

    if parsed_toughness is None or parsed_save is None or parsed_wounds is None:
        raise ValueError("Target profile is missing toughness, save, or wound data.")

    return TargetProfile(
        name=name,
        toughness=parsed_toughness,
        save=parsed_save,
        invulnerable_save=parsed_invulnerable,
        wounds_per_model=parsed_wounds,
        model_count=model_count,
        keywords=tuple(keywords),
        in_cover=in_cover,
    )


def wound_threshold(strength: int, toughness: int) -> int:
    if strength >= toughness * 2:
        return 2
    if strength > toughness:
        return 3
    if strength == toughness:
        return 4
    if strength * 2 <= toughness:
        return 6
    return 5


def evaluate_roll(
    roll: int, threshold: int, modifier: int, *, crit_threshold: int = 6
) -> tuple[bool, bool]:
    if roll == 1:
        return False, False
    if roll >= crit_threshold:
        return True, True
    return (roll + modifier) >= threshold, False


def should_reroll(roll: int, success: bool, reroll_mode: RerollMode) -> bool:
    if reroll_mode == "ones":
        return roll == 1
    if reroll_mode == "fails":
        return not success
    return False


def roll_probabilities(
    threshold: int,
    modifier: int,
    reroll_mode: RerollMode,
    *,
    crit_threshold: int = 6,
) -> RollProbabilities:
    success_noncrit = 0.0
    crit = 0.0
    fail = 0.0

    for first_roll in range(1, 7):
        first_success, first_crit = evaluate_roll(
            first_roll, threshold, modifier, crit_threshold=crit_threshold
        )
        if should_reroll(first_roll, first_success, reroll_mode):
            for second_roll in range(1, 7):
                rerolled_success, rerolled_crit = evaluate_roll(
                    second_roll,
                    threshold,
                    modifier,
                    crit_threshold=crit_threshold,
                )
                weight = 1.0 / 36.0
                if rerolled_crit:
                    crit += weight
                elif rerolled_success:
                    success_noncrit += weight
                else:
                    fail += weight
            continue

        weight = 1.0 / 6.0
        if first_crit:
            crit += weight
        elif first_success:
            success_noncrit += weight
        else:
            fail += weight

    return RollProbabilities(success_noncrit=success_noncrit, crit=crit, fail=fail)


def average_roll_probabilities(
    strength: DiceExpression,
    target_toughness: int,
    modifier: int,
    reroll_mode: RerollMode,
    *,
    crit_threshold: int = 6,
) -> RollProbabilities:
    success_noncrit = 0.0
    crit = 0.0
    fail = 0.0

    for strength_value, probability in strength.distribution().items():
        threshold = wound_threshold(strength_value, target_toughness)
        chances = roll_probabilities(
            threshold,
            modifier,
            reroll_mode,
            crit_threshold=crit_threshold,
        )
        success_noncrit += chances.success_noncrit * probability
        crit += chances.crit * probability
        fail += chances.fail * probability

    return RollProbabilities(success_noncrit=success_noncrit, crit=crit, fail=fail)


def add_distributions(left: dict[int, float], right: dict[int, float]) -> dict[int, float]:
    combined: Counter[int] = Counter()
    for left_value, left_probability in left.items():
        for right_value, right_probability in right.items():
            combined[left_value + right_value] += left_probability * right_probability
    return dict(sorted(combined.items()))


def shift_distribution(distribution: dict[int, float], shift: int) -> dict[int, float]:
    shifted: Counter[int] = Counter()
    for value, probability in distribution.items():
        shifted[value + shift] += probability
    return dict(sorted(shifted.items()))


def attack_distribution(
    weapon: CombatWeaponProfile, target: TargetProfile, context: AttackContext
) -> dict[int, float]:
    distribution = weapon.attacks.distribution()

    if context.half_range and weapon.rules.rapid_fire:
        distribution = add_distributions(distribution, weapon.rules.rapid_fire.distribution())

    if weapon.rules.blast:
        distribution = shift_distribution(distribution, target.model_count // 5)
        if target.model_count >= 10:
            normalized: Counter[int] = Counter()
            for attack_count, probability in distribution.items():
                normalized[max(attack_count, 3)] += probability
            distribution = dict(sorted(normalized.items()))

    return distribution


def damage_distribution(weapon: CombatWeaponProfile, context: AttackContext) -> dict[int, float]:
    distribution = weapon.damage.distribution()
    if context.half_range and weapon.rules.melta:
        distribution = add_distributions(distribution, weapon.rules.melta.distribution())
    return distribution


def mean_from_distribution(distribution: dict[int, float]) -> float:
    return sum(value * probability for value, probability in distribution.items())


def effective_hit_modifier(weapon: CombatWeaponProfile, context: AttackContext) -> int:
    extra = (
        1 if context.stationary and weapon.rules.heavy and weapon.kind.lower() == "ranged" else 0
    )
    return clamp_modifier(context.hit_modifier + extra)


def effective_wound_modifier(weapon: CombatWeaponProfile, context: AttackContext) -> int:
    extra = 1 if context.charged and weapon.rules.lance and weapon.kind.lower() == "melee" else 0
    return clamp_modifier(context.wound_modifier + extra)


def anti_threshold_for_target(weapon: CombatWeaponProfile, target: TargetProfile) -> int:
    if not weapon.rules.anti_keyword or weapon.rules.anti_threshold is None:
        return 6

    wanted = normalize_keyword(weapon.rules.anti_keyword)
    target_keywords = {normalize_keyword(keyword) for keyword in target.keywords}
    if wanted in target_keywords:
        return weapon.rules.anti_threshold
    return 6


def save_target(weapon: CombatWeaponProfile, target: TargetProfile) -> int | None:
    cover_bonus = (
        1
        if target.in_cover and weapon.kind.lower() == "ranged" and not weapon.rules.ignores_cover
        else 0
    )
    armor_target = max(2, target.save - cover_bonus - weapon.ap)
    candidates = []
    if armor_target <= 6:
        candidates.append(armor_target)
    if target.invulnerable_save is not None:
        candidates.append(target.invulnerable_save)
    return min(candidates) if candidates else None


def save_fail_probability(required_roll: int | None) -> float:
    if required_roll is None or required_roll > 6:
        return 1.0
    if required_roll <= 2:
        return 1.0 / 6.0
    failures = sum(1 for roll in range(1, 7) if roll == 1 or roll < required_roll)
    return failures / 6.0


def percentile(values: list[int], percentile_value: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    position = round((len(sorted_values) - 1) * percentile_value)
    return float(sorted_values[position])


def apply_damage(
    target: TargetProfile,
    damage: int,
    *,
    wounds_remaining_on_current_model: int,
    models_slain: int,
) -> tuple[int, int, int]:
    if models_slain >= target.model_count:
        return wounds_remaining_on_current_model, models_slain, 0

    wounds_applied = min(damage, wounds_remaining_on_current_model)
    wounds_remaining_on_current_model -= damage

    if wounds_remaining_on_current_model <= 0:
        models_slain += 1
        if models_slain < target.model_count:
            wounds_remaining_on_current_model = target.wounds_per_model
        else:
            wounds_remaining_on_current_model = 0

    return wounds_remaining_on_current_model, models_slain, wounds_applied


def roll_save(required_roll: int | None, rng: random.Random) -> bool:
    if required_roll is None or required_roll > 6:
        return False
    roll = rng.randint(1, 6)
    if roll == 1:
        return False
    return roll >= required_roll


class CombatSimulator:
    def simulate(
        self,
        weapon: CombatWeaponProfile,
        target: TargetProfile,
        context: AttackContext,
    ) -> CombatSimulationResult:
        hit_modifier = effective_hit_modifier(weapon, context)
        wound_modifier = effective_wound_modifier(weapon, context)

        expected = self._calculate_expected_outcome(
            weapon=weapon,
            target=target,
            context=context,
            hit_modifier=hit_modifier,
            wound_modifier=wound_modifier,
        )
        monte_carlo = self._run_monte_carlo(
            weapon=weapon,
            target=target,
            context=context,
            hit_modifier=hit_modifier,
            wound_modifier=wound_modifier,
        )
        return CombatSimulationResult(
            expected=expected,
            monte_carlo=monte_carlo,
            supported_rules=weapon.rules.supported_rules,
            ignored_rules=weapon.rules.ignored_rules,
            effective_hit_modifier=hit_modifier,
            effective_wound_modifier=wound_modifier,
        )

    def _calculate_expected_outcome(
        self,
        *,
        weapon: CombatWeaponProfile,
        target: TargetProfile,
        context: AttackContext,
        hit_modifier: int,
        wound_modifier: int,
    ) -> ExpectedCombatOutcome:
        per_model_attack_distribution = attack_distribution(weapon, target, context)
        attacks_per_model = mean_from_distribution(per_model_attack_distribution)
        total_attacks = context.attacker_models * attacks_per_model

        if weapon.rules.torrent:
            expected_hits = total_attacks
            auto_wounds = 0.0
            wound_rolls = total_attacks
        else:
            hit_chances = roll_probabilities(
                weapon.skill or 7,
                hit_modifier,
                context.hit_reroll,
            )
            sustained_hits = (
                weapon.rules.sustained_hits.mean() if weapon.rules.sustained_hits else 0.0
            )

            if weapon.rules.lethal_hits:
                auto_wounds = total_attacks * hit_chances.crit
                wound_rolls = total_attacks * (
                    hit_chances.success_noncrit + (hit_chances.crit * sustained_hits)
                )
                expected_hits = total_attacks * (
                    hit_chances.success_noncrit + hit_chances.crit * (1 + sustained_hits)
                )
            else:
                auto_wounds = 0.0
                wound_rolls = total_attacks * (
                    hit_chances.success_noncrit + hit_chances.crit * (1 + sustained_hits)
                )
                expected_hits = wound_rolls

        crit_threshold = anti_threshold_for_target(weapon, target)
        wound_reroll_mode: RerollMode = (
            "fails" if weapon.rules.twin_linked else context.wound_reroll
        )
        wound_chances = average_roll_probabilities(
            weapon.strength,
            target.toughness,
            wound_modifier,
            wound_reroll_mode,
            crit_threshold=crit_threshold,
        )

        regular_wounds = wound_rolls * wound_chances.success_noncrit
        critical_wounds = wound_rolls * wound_chances.crit
        total_wounds = auto_wounds + regular_wounds + critical_wounds

        failed_save_chance = save_fail_probability(save_target(weapon, target))
        regular_unsaved_wounds = (auto_wounds + regular_wounds) * failed_save_chance
        critical_unsaved_wounds = (
            critical_wounds
            if weapon.rules.devastating_wounds
            else critical_wounds * failed_save_chance
        )
        total_unsaved_wounds = regular_unsaved_wounds + critical_unsaved_wounds

        average_damage = mean_from_distribution(damage_distribution(weapon, context))
        raw_damage = total_unsaved_wounds * average_damage

        return ExpectedCombatOutcome(
            attacks=total_attacks,
            hits=expected_hits,
            wounds=total_wounds,
            unsaved_wounds=total_unsaved_wounds,
            raw_damage=raw_damage,
        )

    def _run_monte_carlo(
        self,
        *,
        weapon: CombatWeaponProfile,
        target: TargetProfile,
        context: AttackContext,
        hit_modifier: int,
        wound_modifier: int,
    ) -> MonteCarloOutcome:
        rng = random.Random(context.seed)
        required_save = save_target(weapon, target)
        critical_wound_threshold = anti_threshold_for_target(weapon, target)
        wound_reroll_mode: RerollMode = (
            "fails" if weapon.rules.twin_linked else context.wound_reroll
        )
        wounds_lost_results: list[int] = []
        raw_damage_results: list[int] = []
        models_slain_results: list[int] = []
        wound_histogram: Counter[int] = Counter()

        for _ in range(context.trials):
            wounds_remaining = target.wounds_per_model
            models_slain = 0
            wounds_lost = 0
            raw_damage = 0

            for _ in range(context.attacker_models):
                attacks = self._roll_attack_count(weapon, target, context, rng)
                for _ in range(attacks):
                    normal_hits = 0
                    auto_wounds = 0

                    if weapon.rules.torrent:
                        normal_hits = 1
                    else:
                        hit_result = self._resolve_roll(
                            threshold=weapon.skill or 7,
                            modifier=hit_modifier,
                            reroll_mode=context.hit_reroll,
                            crit_threshold=6,
                            rng=rng,
                        )
                        if hit_result == "fail":
                            continue
                        if hit_result == "crit":
                            if weapon.rules.sustained_hits:
                                normal_hits += weapon.rules.sustained_hits.roll(rng)
                            if weapon.rules.lethal_hits:
                                auto_wounds += 1
                            else:
                                normal_hits += 1
                        elif hit_result == "success":
                            normal_hits += 1

                    for _ in range(auto_wounds):
                        if not roll_save(required_save, rng):
                            damage = self._roll_damage(weapon, context, rng)
                            raw_damage += damage
                            wounds_remaining, models_slain, applied = apply_damage(
                                target,
                                damage,
                                wounds_remaining_on_current_model=wounds_remaining,
                                models_slain=models_slain,
                            )
                            wounds_lost += applied

                    for _ in range(normal_hits):
                        strength = weapon.strength.roll(rng)
                        wound_result = self._resolve_roll(
                            threshold=wound_threshold(strength, target.toughness),
                            modifier=wound_modifier,
                            reroll_mode=wound_reroll_mode,
                            crit_threshold=critical_wound_threshold,
                            rng=rng,
                        )
                        if wound_result == "fail":
                            continue

                        unsaved = wound_result == "crit" and weapon.rules.devastating_wounds
                        if not unsaved:
                            unsaved = not roll_save(required_save, rng)
                        if not unsaved:
                            continue

                        damage = self._roll_damage(weapon, context, rng)
                        raw_damage += damage
                        wounds_remaining, models_slain, applied = apply_damage(
                            target,
                            damage,
                            wounds_remaining_on_current_model=wounds_remaining,
                            models_slain=models_slain,
                        )
                        wounds_lost += applied

            wounds_lost_results.append(wounds_lost)
            raw_damage_results.append(raw_damage)
            models_slain_results.append(models_slain)
            wound_histogram[wounds_lost] += 1

        histogram = tuple(
            HistogramBucket(
                wounds_lost=wounds_lost,
                occurrences=occurrences,
                probability=occurrences / context.trials,
            )
            for wounds_lost, occurrences in sorted(wound_histogram.items())
        )

        kills = sum(
            1 for models_slain in models_slain_results if models_slain >= target.model_count
        )
        return MonteCarloOutcome(
            trials=context.trials,
            average_raw_damage=sum(raw_damage_results) / context.trials,
            average_wounds_lost=sum(wounds_lost_results) / context.trials,
            average_models_slain=sum(models_slain_results) / context.trials,
            kill_probability=kills / context.trials,
            p10_wounds_lost=percentile(wounds_lost_results, 0.10),
            median_wounds_lost=percentile(wounds_lost_results, 0.50),
            p90_wounds_lost=percentile(wounds_lost_results, 0.90),
            histogram=histogram,
        )

    def _roll_attack_count(
        self,
        weapon: CombatWeaponProfile,
        target: TargetProfile,
        context: AttackContext,
        rng: random.Random,
    ) -> int:
        attacks = weapon.attacks.roll(rng)
        if context.half_range and weapon.rules.rapid_fire:
            attacks += weapon.rules.rapid_fire.roll(rng)
        if weapon.rules.blast:
            attacks += target.model_count // 5
            if target.model_count >= 10:
                attacks = max(attacks, 3)
        return max(attacks, 0)

    def _roll_damage(
        self,
        weapon: CombatWeaponProfile,
        context: AttackContext,
        rng: random.Random,
    ) -> int:
        damage = weapon.damage.roll(rng)
        if context.half_range and weapon.rules.melta:
            damage += weapon.rules.melta.roll(rng)
        return max(damage, 0)

    def _resolve_roll(
        self,
        *,
        threshold: int,
        modifier: int,
        reroll_mode: RerollMode,
        crit_threshold: int,
        rng: random.Random,
    ) -> Literal["crit", "success", "fail"]:
        roll = rng.randint(1, 6)
        success, crit = evaluate_roll(roll, threshold, modifier, crit_threshold=crit_threshold)
        if should_reroll(roll, success, reroll_mode):
            roll = rng.randint(1, 6)
            success, crit = evaluate_roll(roll, threshold, modifier, crit_threshold=crit_threshold)

        if crit:
            return "crit"
        if success:
            return "success"
        return "fail"
