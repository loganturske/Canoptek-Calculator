from __future__ import annotations

from dataclasses import dataclass

from ..models import (
    Ability,
    Datasheet,
    DatasheetAbility,
    DatasheetDetachmentAbility,
    DatasheetEnhancement,
    DatasheetKeyword,
    DatasheetLeader,
    DatasheetModel,
    DatasheetModelCost,
    DatasheetOption,
    DatasheetStratagem,
    DatasheetUnitComposition,
    DatasheetWargear,
    Detachment,
    DetachmentAbility,
    Enhancement,
    Faction,
    LastUpdate,
    Source,
    Stratagem,
)
from .schemas import (
    AbilityCSVRow,
    CSVRowModel,
    DatasheetAbilityCSVRow,
    DatasheetCSVRow,
    DatasheetDetachmentAbilityCSVRow,
    DatasheetEnhancementCSVRow,
    DatasheetKeywordCSVRow,
    DatasheetLeaderCSVRow,
    DatasheetModelCostCSVRow,
    DatasheetModelCSVRow,
    DatasheetOptionCSVRow,
    DatasheetStratagemCSVRow,
    DatasheetUnitCompositionCSVRow,
    DatasheetWargearCSVRow,
    DetachmentAbilityCSVRow,
    DetachmentCSVRow,
    EnhancementCSVRow,
    FactionCSVRow,
    LastUpdateCSVRow,
    SourceCSVRow,
    StratagemCSVRow,
)

type RowModelType = type[CSVRowModel]


@dataclass(frozen=True)
class ExportTableDefinition:
    filename: str
    row_model: RowModelType
    orm_model: type
    dedupe_fields: tuple[str, ...] = ()
    skip_if_missing_fields: tuple[str, ...] = ()


EXPORT_TABLES: tuple[ExportTableDefinition, ...] = (
    ExportTableDefinition("Factions.csv", FactionCSVRow, Faction),
    ExportTableDefinition("Source.csv", SourceCSVRow, Source),
    ExportTableDefinition("Detachments.csv", DetachmentCSVRow, Detachment),
    ExportTableDefinition("Abilities.csv", AbilityCSVRow, Ability, dedupe_fields=("id",)),
    ExportTableDefinition("Stratagems.csv", StratagemCSVRow, Stratagem),
    ExportTableDefinition("Enhancements.csv", EnhancementCSVRow, Enhancement),
    ExportTableDefinition("Detachment_abilities.csv", DetachmentAbilityCSVRow, DetachmentAbility),
    ExportTableDefinition("Datasheets.csv", DatasheetCSVRow, Datasheet),
    ExportTableDefinition(
        "Datasheets_abilities.csv",
        DatasheetAbilityCSVRow,
        DatasheetAbility,
        dedupe_fields=("datasheet_id", "line"),
        skip_if_missing_fields=("line",),
    ),
    ExportTableDefinition(
        "Datasheets_keywords.csv",
        DatasheetKeywordCSVRow,
        DatasheetKeyword,
        dedupe_fields=("datasheet_id", "keyword", "model", "is_faction_keyword"),
        skip_if_missing_fields=("keyword",),
    ),
    ExportTableDefinition(
        "Datasheets_models.csv",
        DatasheetModelCSVRow,
        DatasheetModel,
        dedupe_fields=("datasheet_id", "line"),
        skip_if_missing_fields=("line",),
    ),
    ExportTableDefinition(
        "Datasheets_options.csv",
        DatasheetOptionCSVRow,
        DatasheetOption,
        dedupe_fields=("datasheet_id", "line"),
        skip_if_missing_fields=("line",),
    ),
    ExportTableDefinition(
        "Datasheets_wargear.csv",
        DatasheetWargearCSVRow,
        DatasheetWargear,
        dedupe_fields=("datasheet_id", "line", "line_in_wargear"),
        skip_if_missing_fields=("line", "name"),
    ),
    ExportTableDefinition(
        "Datasheets_unit_composition.csv",
        DatasheetUnitCompositionCSVRow,
        DatasheetUnitComposition,
        dedupe_fields=("datasheet_id", "line"),
        skip_if_missing_fields=("line",),
    ),
    ExportTableDefinition(
        "Datasheets_models_cost.csv",
        DatasheetModelCostCSVRow,
        DatasheetModelCost,
        dedupe_fields=("datasheet_id", "line"),
        skip_if_missing_fields=("line",),
    ),
    ExportTableDefinition(
        "Datasheets_stratagems.csv",
        DatasheetStratagemCSVRow,
        DatasheetStratagem,
        dedupe_fields=("datasheet_id", "stratagem_id"),
    ),
    ExportTableDefinition(
        "Datasheets_enhancements.csv",
        DatasheetEnhancementCSVRow,
        DatasheetEnhancement,
        dedupe_fields=("datasheet_id", "enhancement_id"),
    ),
    ExportTableDefinition(
        "Datasheets_detachment_abilities.csv",
        DatasheetDetachmentAbilityCSVRow,
        DatasheetDetachmentAbility,
        dedupe_fields=("datasheet_id", "detachment_ability_id"),
    ),
    ExportTableDefinition(
        "Datasheets_leader.csv",
        DatasheetLeaderCSVRow,
        DatasheetLeader,
        dedupe_fields=("leader_id", "attached_id"),
    ),
    ExportTableDefinition("Last_update.csv", LastUpdateCSVRow, LastUpdate),
)

EXPORT_TABLES_BY_FILENAME = {table.filename: table for table in EXPORT_TABLES}
EXPECTED_EXPORT_FILES = {table.filename for table in EXPORT_TABLES}
