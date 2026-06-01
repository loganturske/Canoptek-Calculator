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
    options: list[DatasheetOptionRead] = Field(default_factory=list)
    unit_composition: list[str] = Field(default_factory=list)
    costs: list[DatasheetCostRead] = Field(default_factory=list)
    models: list[ModelProfileRead] = Field(default_factory=list)
    weapons: list[WeaponProfileRead] = Field(default_factory=list)
    stratagems: list[RuleReferenceRead] = Field(default_factory=list)
    enhancements: list[RuleReferenceRead] = Field(default_factory=list)
    detachment_abilities: list[RuleReferenceRead] = Field(default_factory=list)


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
    supported_rules: list[str]
    ignored_rules: list[str]
    effective_hit_modifier: int
    effective_wound_modifier: int
    expected: SimulationExpectedRead
    monte_carlo: SimulationMonteCarloRead


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attacker_weapon_id: int = Field(gt=0)
    attacker_models: int = Field(default=1, ge=1, le=60)
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
