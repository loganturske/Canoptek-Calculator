from __future__ import annotations

import hashlib
import json
import posixpath
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from pydantic import BaseModel, ConfigDict

from ..config import get_settings
from .registry import EXPECTED_EXPORT_FILES

SPREADSHEET_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

PACKAGE_REL_NS = {
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


@dataclass(frozen=True)
class RemoteExportFile:
    name: str
    url: str


@dataclass(frozen=True)
class WahapediaExportSpec:
    game_system: str
    spec_url: str
    files: tuple[RemoteExportFile, ...]


class DownloadedFixtureFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str
    sha256: str
    bytes: int


class FixtureManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = "wahapedia"
    game_system: str
    spec_url: str
    downloaded_at: datetime
    files: list[DownloadedFixtureFile]


class WahapediaSpecParser:
    """Parse Wahapedia's Excel workbook that lists downloadable CSV exports."""

    def parse(
        self, workbook_bytes: bytes, *, game_system: str, spec_url: str
    ) -> WahapediaExportSpec:
        with zipfile.ZipFile(BytesIO(workbook_bytes)) as archive:
            shared_strings = self._read_shared_strings(archive)
            sheet_path = self._find_sheet_path(archive, "EN")
            sheet_xml = ElementTree.fromstring(archive.read(sheet_path))
            hyperlink_targets = self._read_sheet_hyperlinks(archive, sheet_path, sheet_xml)
            cell_values = self._read_sheet_values(sheet_xml, shared_strings)

        files: list[RemoteExportFile] = []
        for cell_ref, target in hyperlink_targets.items():
            if not target.lower().endswith(".csv"):
                continue

            file_name = cell_values.get(cell_ref) or Path(urlparse(target).path).name
            files.append(RemoteExportFile(name=file_name, url=target))

        files.sort(key=lambda item: item.name)
        discovered_names = {item.name for item in files}
        missing_files = EXPECTED_EXPORT_FILES - discovered_names
        if missing_files:
            raise ValueError(
                "The Wahapedia export spec is missing expected files: "
                + ", ".join(sorted(missing_files))
            )

        return WahapediaExportSpec(
            game_system=game_system,
            spec_url=spec_url,
            files=tuple(files),
        )

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        shared_strings_path = "xl/sharedStrings.xml"
        if shared_strings_path not in archive.namelist():
            return []

        root = ElementTree.fromstring(archive.read(shared_strings_path))
        shared_strings: list[str] = []
        for shared_string in root.findall("a:si", SPREADSHEET_NS):
            text = "".join(
                node.text or "" for node in shared_string.iterfind(".//a:t", SPREADSHEET_NS)
            )
            shared_strings.append(text)
        return shared_strings

    def _find_sheet_path(self, archive: zipfile.ZipFile, sheet_name: str) -> str:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in workbook_rels}

        sheets = workbook.find("a:sheets", SPREADSHEET_NS)
        if sheets is None:
            raise ValueError("Workbook does not contain any sheets.")

        for sheet in sheets:
            if sheet.attrib.get("name") != sheet_name:
                continue
            relationship_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            return posixpath.normpath(posixpath.join("xl", rel_targets[relationship_id]))

        raise ValueError(f"Unable to locate sheet {sheet_name!r} in the export workbook.")

    def _read_sheet_hyperlinks(
        self,
        archive: zipfile.ZipFile,
        sheet_path: str,
        sheet_xml: ElementTree.Element,
    ) -> dict[str, str]:
        parsed_path = Path(sheet_path)
        relationships_path = (parsed_path.parent / "_rels" / f"{parsed_path.name}.rels").as_posix()
        if relationships_path not in archive.namelist():
            return {}

        relationships = ElementTree.fromstring(archive.read(relationships_path))
        rel_targets = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
        hyperlink_targets: dict[str, str] = {}
        for hyperlink in sheet_xml.findall("a:hyperlinks/a:hyperlink", SPREADSHEET_NS):
            cell_ref = hyperlink.attrib["ref"]
            relationship_id = hyperlink.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            )
            if relationship_id and relationship_id in rel_targets:
                hyperlink_targets[cell_ref] = rel_targets[relationship_id]
        return hyperlink_targets

    def _read_sheet_values(
        self,
        sheet_xml: ElementTree.Element,
        shared_strings: list[str],
    ) -> dict[str, str]:
        values: dict[str, str] = {}
        for row in sheet_xml.findall("a:sheetData/a:row", SPREADSHEET_NS):
            for cell in row.findall("a:c", SPREADSHEET_NS):
                cell_ref = cell.attrib["r"]
                cell_type = cell.attrib.get("t")
                raw_value = cell.find("a:v", SPREADSHEET_NS)
                inline_value = cell.find("a:is", SPREADSHEET_NS)

                if inline_value is not None:
                    values[cell_ref] = "".join(
                        node.text or "" for node in inline_value.iterfind(".//a:t", SPREADSHEET_NS)
                    )
                    continue

                if raw_value is None:
                    continue

                if cell_type == "s":
                    values[cell_ref] = shared_strings[int(raw_value.text or "0")]
                else:
                    values[cell_ref] = raw_value.text or ""
        return values


class WahapediaClient:
    """Download Wahapedia export specs and CSV fixtures for Warhammer 40,000."""

    def __init__(self, *, timeout_seconds: float = 60.0) -> None:
        self.settings = get_settings()
        self.timeout = httpx.Timeout(timeout_seconds)
        self.parser = WahapediaSpecParser()

    @property
    def spec_url(self) -> str:
        return (
            f"{self.settings.wahapedia_base_url}/"
            f"{self.settings.wahapedia_game_system}/Export%20Data%20Specs.xlsx"
        )

    def fetch_export_spec(self) -> tuple[WahapediaExportSpec, bytes]:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(self.spec_url)
            response.raise_for_status()
            spec_bytes = response.content

        export_spec = self.parser.parse(
            spec_bytes,
            game_system=self.settings.wahapedia_game_system,
            spec_url=self.spec_url,
        )
        return export_spec, spec_bytes

    def download_exports(self, destination: Path) -> FixtureManifest:
        destination.mkdir(parents=True, exist_ok=True)
        export_spec, spec_bytes = self.fetch_export_spec()
        (destination / "Export Data Specs.xlsx").write_bytes(spec_bytes)

        downloaded_files: list[DownloadedFixtureFile] = []
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for export_file in export_spec.files:
                response = client.get(export_file.url)
                response.raise_for_status()
                payload = response.content
                target_path = destination / export_file.name
                target_path.write_bytes(payload)
                downloaded_files.append(
                    DownloadedFixtureFile(
                        name=export_file.name,
                        url=export_file.url,
                        sha256=hashlib.sha256(payload).hexdigest(),
                        bytes=len(payload),
                    )
                )

        manifest = FixtureManifest(
            game_system=export_spec.game_system,
            spec_url=export_spec.spec_url,
            downloaded_at=datetime.now(tz=UTC),
            files=downloaded_files,
        )
        self.write_manifest(destination, manifest)
        return manifest

    def write_manifest(self, destination: Path, manifest: FixtureManifest) -> Path:
        manifest_path = destination / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return manifest_path

    @staticmethod
    def load_manifest(destination: Path) -> FixtureManifest | None:
        manifest_path = destination / "manifest.json"
        if not manifest_path.exists():
            return None
        return FixtureManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def json_serializer(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True)
