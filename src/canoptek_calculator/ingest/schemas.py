from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WAHAPEDIA_DATETIME_FORMATS = (
    "%d.%m.%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def parse_wahapedia_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    if not isinstance(value, str):
        raise ValueError(f"Expected a datetime string, received {value!r}.")

    cleaned = value.strip()
    for fmt in WAHAPEDIA_DATETIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported Wahapedia datetime format: {value!r}")


class CSVRowModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_blanks(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if not key:
                continue
            if isinstance(value, str):
                stripped = value.strip()
                cleaned[key] = stripped if stripped else None
            else:
                cleaned[key] = value
        return cleaned


class FactionCSVRow(CSVRowModel):
    id: str
    name: str
    link: str


class SourceCSVRow(CSVRowModel):
    id: str
    name: str
    type: str
    edition: str | None = None
    version: str | None = None
    errata_date: datetime
    errata_link: str | None = None

    @field_validator("edition", "version", "errata_link", mode="before")
    @classmethod
    def blank_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("errata_date", mode="before")
    @classmethod
    def parse_errata_date(cls, value: Any) -> datetime:
        return parse_wahapedia_datetime(value)


class DatasheetCSVRow(CSVRowModel):
    id: str
    name: str
    faction_id: str
    source_id: str | None = None
    legend: str | None = None
    role: str | None = None
    loadout: str | None = None
    transport: str | None = None
    virtual: bool
    leader_head: str | None = None
    leader_footer: str | None = None
    damaged_w: str | None = None
    damaged_description: str | None = None
    link: str | None = None


class DatasheetAbilityCSVRow(CSVRowModel):
    datasheet_id: str
    line: int
    ability_id: str | None = None
    model: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    parameter: str | None = None


class DatasheetKeywordCSVRow(CSVRowModel):
    datasheet_id: str
    keyword: str
    model: str | None = None
    is_faction_keyword: bool


class DatasheetModelCSVRow(CSVRowModel):
    datasheet_id: str
    line: int
    name: str | None = None
    m: str | None = Field(default=None, alias="M")
    t: str | None = Field(default=None, alias="T")
    sv: str | None = Field(default=None, alias="Sv")
    inv_sv: str | None = None
    inv_sv_descr: str | None = None
    w: str | None = Field(default=None, alias="W")
    ld: str | None = Field(default=None, alias="Ld")
    oc: str | None = Field(default=None, alias="OC")
    base_size: str | None = None
    base_size_descr: str | None = None


class DatasheetOptionCSVRow(CSVRowModel):
    datasheet_id: str
    line: int
    button: str | None = None
    description: str | None = None


class DatasheetWargearCSVRow(CSVRowModel):
    datasheet_id: str
    line: int
    line_in_wargear: int
    dice: str | None = None
    name: str
    description: str | None = None
    range: str | None = None
    type: str | None = None
    a: str | None = Field(default=None, alias="A")
    bs_ws: str | None = Field(default=None, alias="BS_WS")
    s: str | None = Field(default=None, alias="S")
    ap: str | None = Field(default=None, alias="AP")
    d: str | None = Field(default=None, alias="D")


class DatasheetUnitCompositionCSVRow(CSVRowModel):
    datasheet_id: str
    line: int
    description: str | None = None


class DatasheetModelCostCSVRow(CSVRowModel):
    datasheet_id: str
    line: int
    description: str | None = None
    cost: int | None = None


class DatasheetStratagemCSVRow(CSVRowModel):
    datasheet_id: str
    stratagem_id: str


class DatasheetEnhancementCSVRow(CSVRowModel):
    datasheet_id: str
    enhancement_id: str


class DatasheetDetachmentAbilityCSVRow(CSVRowModel):
    datasheet_id: str
    detachment_ability_id: str


class DatasheetLeaderCSVRow(CSVRowModel):
    leader_id: str
    attached_id: str


class AbilityCSVRow(CSVRowModel):
    id: str
    name: str
    legend: str | None = None
    faction_id: str | None = None
    description: str | None = None


class StratagemCSVRow(CSVRowModel):
    faction_id: str | None = None
    name: str
    id: str
    type: str | None = None
    cp_cost: int | None = None
    legend: str | None = None
    turn: str | None = None
    phase: str | None = None
    detachment: str | None = None
    detachment_id: str | None = None
    description: str | None = None


class EnhancementCSVRow(CSVRowModel):
    faction_id: str | None = None
    id: str
    name: str
    cost: int | None = None
    detachment: str | None = None
    detachment_id: str | None = None
    legend: str | None = None
    description: str | None = None


class DetachmentAbilityCSVRow(CSVRowModel):
    id: str
    faction_id: str | None = None
    name: str
    legend: str | None = None
    description: str | None = None
    detachment: str | None = None
    detachment_id: str | None = None


class DetachmentCSVRow(CSVRowModel):
    id: str
    faction_id: str | None = None
    name: str
    legend: str | None = None
    type: str | None = None


class LastUpdateCSVRow(CSVRowModel):
    singleton_id: int = 1
    last_update: datetime

    @field_validator("last_update", mode="before")
    @classmethod
    def parse_last_update(cls, value: Any) -> datetime:
        return parse_wahapedia_datetime(value)
