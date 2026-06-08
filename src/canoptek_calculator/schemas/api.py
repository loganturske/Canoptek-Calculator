from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DashboardStatsRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixtures_dir: str
    faction_count: int
    datasheet_count: int
    weapon_count: int
    last_update: datetime | None
    last_downloaded_at: datetime | None
    fixture_file_count: int = 0


class FactionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    link: str


class DatasheetSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    faction_id: str
    faction_name: str
    source_name: str
    role: str | None = None
    virtual: bool
    link: str | None = None


class DatasheetAbilityRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ability_type: str | None = None
    parameter: str | None = None
    model: str | None = None
    description_html: str | None = None


class DatasheetOptionRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    button: str | None = None
    description_html: str | None = None


class DatasheetCostRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    cost: int | None = None


class RuleReferenceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    subtitle: str | None = None
    cost: int | None = None
    description_html: str | None = None


class DatasheetReferenceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    faction_name: str
    role: str | None = None


class ModelProfileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: int
    line: int
    name: str
    movement: str | None = None
    toughness: int | None = None
    save: int | None = None
    invulnerable_save: int | None = None
    wounds: int | None = None
    leadership: str | None = None
    objective_control: str | None = None
    base_size: str | None = None
    base_size_description: str | None = None


class WeaponProfileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weapon_id: int
    line: int
    line_in_wargear: int
    name: str
    weapon_type: str | None = None
    range: str | None = None
    attacks: str | None = None
    skill: str | None = None
    strength: str | None = None
    armour_penetration: str | None = None
    damage: str | None = None
    description_html: str | None = None
    rules: list[str] = Field(default_factory=list)
    ignored_rules: list[str] = Field(default_factory=list)
    is_simulatable: bool
    simulation_issue: str | None = None


class DatasheetDetailRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    faction_id: str
    faction_name: str
    source_name: str
    role: str | None = None
    legend_html: str | None = None
    loadout_html: str | None = None
    transport_html: str | None = None
    leader_head_html: str | None = None
    leader_footer_html: str | None = None
    damaged_profile_label: str | None = None
    damaged_profile_html: str | None = None
    link: str | None = None
    keywords: list[str] = Field(default_factory=list)
    abilities: list[DatasheetAbilityRead] = Field(default_factory=list)
    attachable_leaders: list[DatasheetReferenceRead] = Field(default_factory=list)
    options: list[DatasheetOptionRead] = Field(default_factory=list)
    unit_composition: list[str] = Field(default_factory=list)
    costs: list[DatasheetCostRead] = Field(default_factory=list)
    models: list[ModelProfileRead] = Field(default_factory=list)
    weapons: list[WeaponProfileRead] = Field(default_factory=list)
    stratagems: list[RuleReferenceRead] = Field(default_factory=list)
    enhancements: list[RuleReferenceRead] = Field(default_factory=list)
    detachment_abilities: list[RuleReferenceRead] = Field(default_factory=list)


class ArmyListCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    faction_id: str = Field(min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=4000)


class ArmyListUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    faction_id: str | None = Field(default=None, min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=4000)


class ArmyListEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasheet_id: str = Field(min_length=1, max_length=32)
    model_line: int | None = Field(default=None, ge=1, le=20)
    unit_size: int = Field(ge=1, le=60)
    quantity: int = Field(default=1, ge=1, le=12)
    points_each: int | None = Field(default=None, ge=0, le=5000)
    cost_label: str | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)
    sort_order: int | None = Field(default=None, ge=0, le=10000)


class ArmyListEntryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasheet_id: str | None = Field(default=None, min_length=1, max_length=32)
    model_line: int | None = Field(default=None, ge=1, le=20)
    unit_size: int | None = Field(default=None, ge=1, le=60)
    quantity: int | None = Field(default=None, ge=1, le=12)
    points_each: int | None = Field(default=None, ge=0, le=5000)
    cost_label: str | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)
    sort_order: int | None = Field(default=None, ge=0, le=10000)


class ArmyListEntryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    army_list_id: int
    display_name: str
    datasheet_id: str
    datasheet_name: str
    datasheet_role: str | None = None
    datasheet_link: str | None = None
    datasheet_available: bool
    model_line: int | None = None
    model_profile_id: int | None = None
    model_name: str | None = None
    model_available: bool | None = None
    unit_size: int
    quantity: int
    entry_model_count: int
    points_each: int | None = None
    total_points: int | None = None
    cost_label: str | None = None
    nickname: str | None = None
    notes: str | None = None
    sort_order: int
    reference_warning: str | None = None
    created_at: datetime
    updated_at: datetime


class ArmyListSummaryRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    name: str
    faction_id: str
    faction_name: str
    faction_available: bool
    notes: str | None = None
    entry_count: int
    total_units: int
    total_models: int
    total_points: int
    has_unpriced_entries: bool
    has_stale_entries: bool
    created_at: datetime
    updated_at: datetime


class ArmyListDetailRead(ArmyListSummaryRead):
    model_config = ConfigDict(extra="forbid")

    entries: list[ArmyListEntryRead] = Field(default_factory=list)


class HistogramBucketRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    wounds_lost: int
    occurrences: int
    probability: float


class SimulationExpectedRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attacks: float
    hits: float
    wounds: float
    unsaved_wounds: float
    raw_damage: float


class SimulationMonteCarloRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trials: int
    average_raw_damage: float
    average_wounds_lost: float
    average_models_slain: float
    kill_probability: float
    p10_wounds_lost: float
    median_wounds_lost: float
    p90_wounds_lost: float
    histogram: list[HistogramBucketRead]


class SimulationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weapon_name: str
    target_name: str
    attacker_leaders: list[str] = Field(default_factory=list)
    applied_effects: list[str] = Field(default_factory=list)
    supported_rules: list[str]
    ignored_rules: list[str]
    effective_hit_modifier: int
    effective_wound_modifier: int
    expected: SimulationExpectedRead
    monte_carlo: SimulationMonteCarloRead


class SimulationBuildEffectRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_datasheet_id: str
    source_name: str
    ability_name: str
    summary: str
    effect_type: str
    scope: Literal["any", "ranged", "melee"] = "any"
    selectable: bool = True
    enabled_by_default: bool = True


class SimulationBuildPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attacker_datasheet_id: str = Field(min_length=1, max_length=32)
    attacker_leader_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_attacker_leaders(self) -> SimulationBuildPreviewRequest:
        if len(self.attacker_leader_ids) > 1:
            raise ValueError(
                "Only one attached leader is currently supported in the Simulation Forge."
            )
        if len(set(self.attacker_leader_ids)) != len(self.attacker_leader_ids):
            raise ValueError("Leader selections must be unique.")
        return self


class SimulationBuildPreviewRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attacker_id: str
    attacker_name: str
    selected_leaders: list[DatasheetReferenceRead] = Field(default_factory=list)
    effects: list[SimulationBuildEffectRead] = Field(default_factory=list)
    unmodeled_abilities: list[str] = Field(default_factory=list)


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attacker_weapon_id: int = Field(gt=0)
    attacker_models: int = Field(default=1, ge=1, le=60)
    attacker_leader_ids: list[str] = Field(default_factory=list)
    attacker_enabled_effect_ids: list[str] | None = None
    defender_mode: Literal["datasheet", "custom"] = "datasheet"
    defender_model_id: int | None = Field(default=None, gt=0)
    target_model_count: int = Field(default=1, ge=1, le=60)
    defender_in_cover: bool = False
    hit_reroll: Literal["none", "ones", "fails"] = "none"
    wound_reroll: Literal["none", "ones", "fails"] = "none"
    hit_modifier: int = Field(default=0, ge=-2, le=2)
    wound_modifier: int = Field(default=0, ge=-2, le=2)
    half_range: bool = False
    stationary: bool = False
    charged: bool = False
    trials: int = Field(default=5000, ge=100, le=50000)
    seed: int | None = None
    custom_target_name: str = "Custom Target"
    custom_toughness: int | None = Field(default=None, ge=1, le=40)
    custom_save: int | None = Field(default=None, ge=2, le=7)
    custom_invulnerable_save: int | None = Field(default=None, ge=2, le=7)
    custom_wounds: int | None = Field(default=None, ge=1, le=99)
    custom_keywords: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_target_selection(self) -> SimulationRequest:
        if len(self.attacker_leader_ids) > 1:
            raise ValueError(
                "Only one attached leader is currently supported in the Simulation Forge."
            )
        if len(set(self.attacker_leader_ids)) != len(self.attacker_leader_ids):
            raise ValueError("Leader selections must be unique.")
        if self.attacker_enabled_effect_ids is not None and len(
            set(self.attacker_enabled_effect_ids)
        ) != len(self.attacker_enabled_effect_ids):
            raise ValueError("Simulation effect selections must be unique.")

        if self.defender_mode == "datasheet" and self.defender_model_id is None:
            raise ValueError("A defender model must be selected in datasheet mode.")

        if self.defender_mode == "custom":
            required_fields = (
                self.custom_toughness,
                self.custom_save,
                self.custom_wounds,
            )
            if any(value is None for value in required_fields):
                raise ValueError("Custom target mode requires toughness, save, and wounds values.")

        return self
