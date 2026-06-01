from __future__ import annotations

import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, func, insert, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from ..db import get_engine, get_session_factory, initialize_database
from ..models import Base, Datasheet
from .registry import EXPORT_TABLES, ExportTableDefinition
from .wahapedia import FixtureManifest, WahapediaClient


class TableImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table: str
    rows_imported: int


class DataSyncResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixtures_dir: str
    downloaded: bool
    imported: bool
    manifest: FixtureManifest | None
    tables: list[TableImportResult]


@dataclass
class DataImportService:
    engine: Engine
    session_factory: sessionmaker[Session]
    wahapedia_client: WahapediaClient
    fixtures_dir: Path

    @classmethod
    def from_defaults(cls) -> DataImportService:
        settings = get_settings()
        return cls(
            engine=get_engine(),
            session_factory=get_session_factory(),
            wahapedia_client=WahapediaClient(),
            fixtures_dir=settings.fixtures_dir,
        )

    def bootstrap(self, *, refresh: bool = False, force_import: bool = False) -> DataSyncResult:
        initialize_database()
        fixtures_exist = self.fixtures_available()
        database_populated = self.database_has_data()
        downloaded = False

        manifest = self.wahapedia_client.load_manifest(self.fixtures_dir)
        if refresh or not fixtures_exist:
            manifest = self.wahapedia_client.download_exports(self.fixtures_dir)
            downloaded = True

        if force_import or downloaded or not database_populated:
            tables = self.import_fixtures(self.fixtures_dir)
            return DataSyncResult(
                fixtures_dir=str(self.fixtures_dir),
                downloaded=downloaded,
                imported=True,
                manifest=manifest,
                tables=tables,
            )

        return DataSyncResult(
            fixtures_dir=str(self.fixtures_dir),
            downloaded=downloaded,
            imported=False,
            manifest=manifest,
            tables=[],
        )

    def sync(self, *, refresh_download: bool = True) -> DataSyncResult:
        initialize_database()
        manifest = (
            self.wahapedia_client.download_exports(self.fixtures_dir)
            if refresh_download
            else self.wahapedia_client.load_manifest(self.fixtures_dir)
        )
        tables = self.import_fixtures(self.fixtures_dir)
        return DataSyncResult(
            fixtures_dir=str(self.fixtures_dir),
            downloaded=refresh_download,
            imported=True,
            manifest=manifest,
            tables=tables,
        )

    def download_fixtures(self, destination: Path | None = None) -> FixtureManifest:
        initialize_database()
        target_dir = destination or self.fixtures_dir
        return self.wahapedia_client.download_exports(target_dir)

    def import_fixtures(self, fixtures_dir: Path | None = None) -> list[TableImportResult]:
        initialize_database()
        target_dir = fixtures_dir or self.fixtures_dir
        self._validate_fixture_directory(target_dir)
        self._reset_schema()

        results: list[TableImportResult] = []
        with self.session_factory() as session:
            for table in EXPORT_TABLES:
                imported_rows = self._import_table(session, target_dir, table)
                results.append(TableImportResult(table=table.filename, rows_imported=imported_rows))
                session.commit()
        return results

    def fixtures_available(self) -> bool:
        return self.fixtures_dir.exists() and all(
            (self.fixtures_dir / table.filename).exists() for table in EXPORT_TABLES
        )

    def database_has_data(self) -> bool:
        with self.session_factory() as session:
            count = session.scalar(select(func.count()).select_from(Datasheet))
        return bool(count)

    def _validate_fixture_directory(self, fixtures_dir: Path) -> None:
        missing = [
            table.filename
            for table in EXPORT_TABLES
            if not (fixtures_dir / table.filename).exists()
        ]
        if missing:
            raise FileNotFoundError(
                f"Fixture directory {fixtures_dir} is missing expected files: {', '.join(missing)}"
            )

    def _reset_schema(self) -> None:
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)

    def _import_table(
        self,
        session: Session,
        fixtures_dir: Path,
        table: ExportTableDefinition,
        *,
        batch_size: int = 1000,
    ) -> int:
        file_path = fixtures_dir / table.filename
        rows_imported = 0
        pending_rows: list[dict[str, object]] = []
        seen_keys: set[tuple[object, ...]] = set()
        for row in self._iter_validated_rows(file_path, table):
            if table.skip_if_missing_fields and any(
                row.get(field_name) in {None, ""} for field_name in table.skip_if_missing_fields
            ):
                continue
            if table.dedupe_fields:
                row_key = tuple(row.get(field_name) for field_name in table.dedupe_fields)
                if row_key in seen_keys:
                    continue
                seen_keys.add(row_key)
            pending_rows.append(row)
            if len(pending_rows) >= batch_size:
                session.execute(insert(table.orm_model), pending_rows)
                rows_imported += len(pending_rows)
                pending_rows.clear()

        if pending_rows:
            session.execute(insert(table.orm_model), pending_rows)
            rows_imported += len(pending_rows)

        return rows_imported

    def _iter_validated_rows(
        self,
        file_path: Path,
        table: ExportTableDefinition,
    ) -> Iterator[dict[str, object]]:
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="|")
            for index, raw_row in enumerate(reader, start=2):
                if table.skip_if_missing_fields and any(
                    not (raw_row.get(field_name) or "").strip()
                    for field_name in table.skip_if_missing_fields
                ):
                    continue
                try:
                    row_model = table.row_model.model_validate(raw_row)
                except Exception as exc:  # pragma: no cover - error path exercised in runtime.
                    raise ValueError(
                        f"Validation failed for {table.filename} line {index}: {exc}"
                    ) from exc

                yield row_model.model_dump(mode="python")


def delete_all_rows(session: Session, orm_model: type) -> int:
    result = session.execute(delete(orm_model))
    return result.rowcount or 0
