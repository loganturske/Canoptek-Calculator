from __future__ import annotations

import csv
from pathlib import Path

import pytest

from canoptek_calculator.config import get_settings
from canoptek_calculator.db import get_engine, get_session_factory


def write_pipe_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="|")
        writer.writeheader()
        writer.writerows(rows)


def create_sample_export_bundle(root: Path) -> Path:
    bundle = root / "fixtures" / "wahapedia" / "wh40k10ed"
    bundle.mkdir(parents=True, exist_ok=True)

    files: dict[str, tuple[list[str], list[dict[str, object]]]] = {
        "Factions.csv": (
            ["id", "name", "link"],
            [
                {"id": "NEC", "name": "Necrons", "link": "https://example.com/factions/necrons"},
                {
                    "id": "SM",
                    "name": "Space Marines",
                    "link": "https://example.com/factions/space-marines",
                },
            ],
        ),
        "Source.csv": (
            ["id", "name", "type", "edition", "version", "errata_date", "errata_link"],
            [
                {
                    "id": "000000001",
                    "name": "Codex Test Data",
                    "type": "Codex",
                    "edition": "10",
                    "version": "1.0",
                    "errata_date": "01.01.2026 0:00:00",
                    "errata_link": "https://example.com/sources/codex-test-data",
                }
            ],
        ),
        "Detachments.csv": (
            ["id", "faction_id", "name", "legend", "type"],
            [
                {
                    "id": "000000100",
                    "faction_id": "NEC",
                    "name": "Awakened Dynasty",
                    "legend": "",
                    "type": "Detachment",
                }
            ],
        ),
        "Abilities.csv": (
            ["id", "name", "legend", "faction_id", "description"],
            [
                {
                    "id": "000000200",
                    "name": "Reanimation Protocols",
                    "legend": "",
                    "faction_id": "NEC",
                    "description": "A reanimation-focused faction rule.",
                }
            ],
        ),
        "Stratagems.csv": (
            [
                "faction_id",
                "name",
                "id",
                "type",
                "cp_cost",
                "legend",
                "turn",
                "phase",
                "detachment",
                "detachment_id",
                "description",
            ],
            [
                {
                    "faction_id": "NEC",
                    "name": "Protocol of the Undying Legions",
                    "id": "000000300",
                    "type": "Battle Tactic Stratagem",
                    "cp_cost": "1",
                    "legend": "",
                    "turn": "Your turn",
                    "phase": "Command phase",
                    "detachment": "Awakened Dynasty",
                    "detachment_id": "000000100",
                    "description": "Repair a nearby Necron unit.",
                }
            ],
        ),
        "Enhancements.csv": (
            [
                "faction_id",
                "id",
                "name",
                "cost",
                "detachment",
                "detachment_id",
                "legend",
                "description",
            ],
            [
                {
                    "faction_id": "NEC",
                    "id": "000000400",
                    "name": "Veil of Darkness",
                    "cost": "20",
                    "detachment": "Awakened Dynasty",
                    "detachment_id": "000000100",
                    "legend": "",
                    "description": "Teleport a friendly unit once per battle.",
                }
            ],
        ),
        "Detachment_abilities.csv": (
            ["id", "faction_id", "name", "legend", "description", "detachment", "detachment_id"],
            [
                {
                    "id": "000000500",
                    "faction_id": "NEC",
                    "name": "Command Protocols",
                    "legend": "",
                    "description": "Issue tactical directives to nearby units.",
                    "detachment": "Awakened Dynasty",
                    "detachment_id": "000000100",
                }
            ],
        ),
        "Datasheets.csv": (
            [
                "id",
                "name",
                "faction_id",
                "source_id",
                "legend",
                "role",
                "loadout",
                "transport",
                "virtual",
                "leader_head",
                "leader_footer",
                "damaged_w",
                "damaged_description",
                "link",
            ],
            [
                {
                    "id": "000000600",
                    "name": "Necron Warriors",
                    "faction_id": "NEC",
                    "source_id": "000000001",
                    "legend": "Rank-and-file Necron infantry.",
                    "role": "Battleline",
                    "loadout": "<b>Every model is equipped with:</b> gauss flayer.",
                    "transport": "",
                    "virtual": "false",
                    "leader_head": "",
                    "leader_footer": "",
                    "damaged_w": "",
                    "damaged_description": "",
                    "link": "https://example.com/datasheets/necron-warriors",
                },
                {
                    "id": "000000601",
                    "name": "Space Marine Intercessors",
                    "faction_id": "SM",
                    "source_id": "000000001",
                    "legend": "Standard Adeptus Astartes infantry.",
                    "role": "Battleline",
                    "loadout": "<b>Every model is equipped with:</b> bolt rifle.",
                    "transport": "",
                    "virtual": "false",
                    "leader_head": "",
                    "leader_footer": "",
                    "damaged_w": "",
                    "damaged_description": "",
                    "link": "https://example.com/datasheets/intercessors",
                },
            ],
        ),
        "Datasheets_abilities.csv": (
            [
                "datasheet_id",
                "line",
                "ability_id",
                "model",
                "name",
                "description",
                "type",
                "parameter",
            ],
            [
                {
                    "datasheet_id": "000000600",
                    "line": "1",
                    "ability_id": "000000200",
                    "model": "",
                    "name": "",
                    "description": "",
                    "type": "Faction",
                    "parameter": "",
                }
            ],
        ),
        "Datasheets_keywords.csv": (
            ["datasheet_id", "keyword", "model", "is_faction_keyword"],
            [
                {
                    "datasheet_id": "000000600",
                    "keyword": "Necrons",
                    "model": "",
                    "is_faction_keyword": "true",
                },
                {
                    "datasheet_id": "000000600",
                    "keyword": "Infantry",
                    "model": "",
                    "is_faction_keyword": "false",
                },
                {
                    "datasheet_id": "000000601",
                    "keyword": "Space Marines",
                    "model": "",
                    "is_faction_keyword": "true",
                },
                {
                    "datasheet_id": "000000601",
                    "keyword": "Infantry",
                    "model": "",
                    "is_faction_keyword": "false",
                },
            ],
        ),
        "Datasheets_models.csv": (
            [
                "datasheet_id",
                "line",
                "name",
                "M",
                "T",
                "Sv",
                "inv_sv",
                "inv_sv_descr",
                "W",
                "Ld",
                "OC",
                "base_size",
                "base_size_descr",
            ],
            [
                {
                    "datasheet_id": "000000600",
                    "line": "1",
                    "name": "Necron Warrior",
                    "M": '5"',
                    "T": "4",
                    "Sv": "4+",
                    "inv_sv": "",
                    "inv_sv_descr": "",
                    "W": "1",
                    "Ld": "7+",
                    "OC": "2",
                    "base_size": "32mm",
                    "base_size_descr": "",
                },
                {
                    "datasheet_id": "000000601",
                    "line": "1",
                    "name": "Intercessor",
                    "M": '6"',
                    "T": "4",
                    "Sv": "3+",
                    "inv_sv": "",
                    "inv_sv_descr": "",
                    "W": "2",
                    "Ld": "6+",
                    "OC": "2",
                    "base_size": "32mm",
                    "base_size_descr": "",
                },
            ],
        ),
        "Datasheets_options.csv": (
            ["datasheet_id", "line", "button", "description"],
            [
                {
                    "datasheet_id": "000000600",
                    "line": "1",
                    "button": "*",
                    "description": (
                        "Any number of models can replace their gauss flayer with a "
                        "gauss reaper."
                    ),
                }
            ],
        ),
        "Datasheets_wargear.csv": (
            [
                "datasheet_id",
                "line",
                "line_in_wargear",
                "dice",
                "name",
                "description",
                "range",
                "type",
                "A",
                "BS_WS",
                "S",
                "AP",
                "D",
            ],
            [
                {
                    "datasheet_id": "000000600",
                    "line": "1",
                    "line_in_wargear": "1",
                    "dice": "",
                    "name": "Gauss flayer",
                    "description": "rapid fire 1, lethal hits",
                    "range": "24",
                    "type": "Ranged",
                    "A": "1",
                    "BS_WS": "4",
                    "S": "4",
                    "AP": "0",
                    "D": "1",
                },
                {
                    "datasheet_id": "000000601",
                    "line": "1",
                    "line_in_wargear": "1",
                    "dice": "",
                    "name": "Bolt rifle",
                    "description": "assault",
                    "range": "24",
                    "type": "Ranged",
                    "A": "2",
                    "BS_WS": "3",
                    "S": "4",
                    "AP": "-1",
                    "D": "1",
                },
            ],
        ),
        "Datasheets_unit_composition.csv": (
            ["datasheet_id", "line", "description"],
            [
                {"datasheet_id": "000000600", "line": "1", "description": "10 Necron Warriors"},
                {"datasheet_id": "000000601", "line": "1", "description": "5 Intercessors"},
            ],
        ),
        "Datasheets_models_cost.csv": (
            ["datasheet_id", "line", "description", "cost"],
            [
                {
                    "datasheet_id": "000000600",
                    "line": "1",
                    "description": "10 models",
                    "cost": "100",
                },
                {"datasheet_id": "000000601", "line": "1", "description": "5 models", "cost": "90"},
            ],
        ),
        "Datasheets_stratagems.csv": (
            ["datasheet_id", "stratagem_id"],
            [{"datasheet_id": "000000600", "stratagem_id": "000000300"}],
        ),
        "Datasheets_enhancements.csv": (
            ["datasheet_id", "enhancement_id"],
            [{"datasheet_id": "000000600", "enhancement_id": "000000400"}],
        ),
        "Datasheets_detachment_abilities.csv": (
            ["datasheet_id", "detachment_ability_id"],
            [{"datasheet_id": "000000600", "detachment_ability_id": "000000500"}],
        ),
        "Datasheets_leader.csv": (
            ["leader_id", "attached_id"],
            [],
        ),
        "Last_update.csv": (
            ["last_update"],
            [{"last_update": "2026-05-09 23:42:21"}],
        ),
    }

    for filename, (headers, rows) in files.items():
        write_pipe_csv(bundle / filename, headers, rows)

    return bundle


@pytest.fixture()
def isolated_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bundle = create_sample_export_bundle(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.sqlite3")
    monkeypatch.setenv("FIXTURES_DIR", str(bundle))

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    yield bundle

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
