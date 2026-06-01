from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

from .config import get_settings
from .ingest.service import DataImportService

app = typer.Typer(help="Canoptek Calculator management commands.")


def _print_table_results(result) -> None:
    typer.echo(f"Fixtures directory: {result.fixtures_dir}")
    if result.manifest is not None:
        typer.echo(f"Downloaded at: {result.manifest.downloaded_at.isoformat()}")
        typer.echo(f"Fixture files: {len(result.manifest.files)}")
    if result.tables:
        typer.echo("Imported tables:")
        for table in result.tables:
            typer.echo(f"  - {table.table}: {table.rows_imported:,} rows")
    else:
        typer.echo("No import was necessary.")


@app.command("download-fixtures")
def download_fixtures(
    destination: Path | None = typer.Option(
        default=None,
        help="Optional destination directory for the downloaded Wahapedia CSV files.",
    ),
) -> None:
    service = DataImportService.from_defaults()
    manifest = service.download_fixtures(destination)
    typer.echo(
        f"Downloaded {len(manifest.files)} fixture files to {destination or service.fixtures_dir}"
    )


@app.command("import-fixtures")
def import_fixtures(
    fixtures_dir: Path | None = typer.Option(
        default=None,
        help="Directory containing the Wahapedia CSV fixture files.",
    ),
) -> None:
    service = DataImportService.from_defaults()
    results = service.import_fixtures(fixtures_dir)
    for table in results:
        typer.echo(f"{table.table}: {table.rows_imported:,} rows imported")


@app.command()
def sync() -> None:
    """Download the latest Wahapedia export and import it into the database."""

    service = DataImportService.from_defaults()
    result = service.sync(refresh_download=True)
    _print_table_results(result)


@app.command()
def bootstrap(
    refresh: bool = typer.Option(
        default=False,
        help="Force a fresh Wahapedia download before bootstrapping.",
    ),
    force_import: bool = typer.Option(
        default=False,
        help="Force an import even if the database already contains datasheets.",
    ),
) -> None:
    """Prepare fixtures and the database for the web app."""

    service = DataImportService.from_defaults()
    result = service.bootstrap(refresh=refresh, force_import=force_import)
    _print_table_results(result)


@app.command()
def serve(
    host: str = typer.Option(default=None, help="Host interface for the FastAPI server."),
    port: int = typer.Option(default=None, help="Port for the FastAPI server."),
    reload: bool = typer.Option(default=False, help="Enable auto-reload for development."),
) -> None:
    """Run the FastAPI application with Uvicorn."""

    settings = get_settings()
    uvicorn.run(
        "canoptek_calculator.main:app",
        host=host or settings.app_host,
        port=port or settings.app_port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
