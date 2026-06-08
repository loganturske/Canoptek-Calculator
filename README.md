# Canoptek Calculator

Canoptek Calculator is a Warhammer 40,000 10th edition data workbench built around Wahapedia's `wh40k10ed` export.

It downloads the published CSV export into a local fixture directory, validates the files with typed Pydantic models, imports them into a relational database, and exposes both a web UI and JSON API for browsing datasheets and running combat simulations.

## What it includes

- A FastAPI application with a built-in frontend for:
  - refreshing Wahapedia 40k export data
  - browsing imported datasheets
  - building and saving army lists with tracked points totals
  - loading saved roster units directly into simulations
  - attaching leaders and toggling imported structured unit effects in the Simulation Forge
  - running expected-value and Monte Carlo combat calculations
- A robust ingestion pipeline that:
  - discovers the current export file list from Wahapedia's published workbook
  - stores CSVs in `fixtures/wahapedia/wh40k10ed`
  - validates rows with typed Pydantic schemas
  - bulk-loads SQLAlchemy models into the database
  - persists structured combat effects for unit abilities during import/sync time
- An AI-ready interpretation layer that:
  - can call OpenAI during import/sync to translate ability text into a structured effect DSL
  - falls back to the deterministic built-in parser when AI is disabled or unavailable
  - keeps simulation runtime deterministic by executing only stored structured effects
- A simulation engine that works from imported weapon/model profiles
- A Docker image and `docker-compose.yml`
- Tests and Ruff linting

## Tech stack

- Backend: FastAPI
- Validation and serialization: Pydantic v2
- Database layer: SQLAlchemy 2
- Default database: SQLite
- Frontend: server-rendered HTML + vanilla JavaScript + CSS
- Packaging: `pyproject.toml`
- Container runtime: Docker

## Project layout

```text
src/canoptek_calculator/
  api/          FastAPI routes and dependencies
  domain/       Dice parsing and combat simulation engine
  ingest/       Wahapedia workbook parsing, CSV download, validation, import
  models/       SQLAlchemy ORM models
  schemas/      API request and response models
  services/     Army list, catalog, and simulation orchestration
  static/       CSS and JavaScript
  templates/    Jinja templates
fixtures/
  wahapedia/
    wh40k10ed/  Downloaded CSV fixtures and manifest
tests/          Import, API, and simulation coverage
```

## Quick start with Docker

### Run the app

```bash
docker compose up --build
```

The container entrypoint will:

1. create the database if needed
2. download Wahapedia CSVs into `fixtures/wahapedia/wh40k10ed` if they are missing
3. import the data if the database is empty
4. start the FastAPI server on port `8000`

### Open the app

Open `http://localhost:8000`

### Useful Docker notes

- The database is persisted in `./data`
- Fixtures are persisted in `./fixtures`
- API docs are available at `http://localhost:8000/api/docs`
- This local stack publishes the app directly on `8000` for development convenience. Do not port-forward this stack to the public internet.

## Safe public exposure

The safer production path in this repo uses a separate Docker Compose stack with:

- Caddy as the public reverse proxy
- automatic HTTPS at the edge
- HTTP Basic Auth in front of the entire site
- the FastAPI app kept on Docker's internal network only

### What you need

- a public domain name pointed at your home/server public IP
- router control so you can forward ports
- TCP ports `80` and `443` forwarded to the machine running Docker

Do not forward port `8000` in the public setup.

### Files involved

- Public compose stack: `docker-compose.public.yml`
- Caddy config: `docker/caddy/Caddyfile`
- Public environment template: `.env.public.example`

### 1. Point a domain at your public IP

Create an `A` record for your chosen hostname, for example:

```text
warhammer.example.com -> your.public.ip.address
```

### 2. Create the public env file

Copy the example file and fill it in:

```bash
cp .env.public.example .env.public
```

Set these values:

- `CANOPTEK_PUBLIC_HOST`
- `CANOPTEK_BASICAUTH_USER`
- `CANOPTEK_BASICAUTH_HASH`
- `APP_ALLOWED_HOSTS`

### 3. Generate the password hash

Caddy requires a hashed password for Basic Auth. You can generate one with Docker:

```bash
docker run --rm caddy:2.10 caddy hash-password --plaintext "replace-this-password"
```

Put the resulting hash into `CANOPTEK_BASICAUTH_HASH`.

### 4. Start the public stack

```bash
docker compose -f docker-compose.public.yml up --build -d
```

This stack:

1. runs the app without publishing port `8000`
2. publishes only `80` and `443` from Caddy
3. terminates HTTPS in Caddy
4. requires Basic Auth before access

### 5. Configure router port forwarding

Forward these ports from your router to the machine running Docker:

- external TCP `80` -> internal TCP `80`
- external TCP `443` -> internal TCP `443`

Do not create a forwarding rule for `8000`.

### 6. Test from outside your network

Open:

```text
https://your-public-hostname
```

Your browser should:

- get a valid HTTPS certificate
- prompt for a username and password
- reach Canoptek Calculator only after successful auth

### Public setup notes

- The app now enforces trusted `Host` headers through `APP_ALLOWED_HOSTS`
- If you are using SQLite, stop the local `docker-compose.yml` stack before running the public stack so both app containers do not share the same database file
- If your ISP blocks inbound `80` or `443`, a tunnel product is safer than opening alternate ports
- If you want per-user access control instead of shared Basic Auth, put this behind a proper identity proxy later

## Local development

### Install dependencies

```bash
python -m pip install -e .[dev]
```

### Bootstrap fixtures and database

```bash
python -m canoptek_calculator.cli bootstrap
```

### Start the app

```bash
python -m canoptek_calculator.cli serve --reload
```

### Open the app

Open `http://127.0.0.1:8000`

## CLI commands

### Download the current Wahapedia export into the fixture directory

```bash
python -m canoptek_calculator.cli download-fixtures
```

### Import the fixture directory into the database

```bash
python -m canoptek_calculator.cli import-fixtures
```

### Download fresh data and import it immediately

```bash
python -m canoptek_calculator.cli sync
```

`sync` and `bootstrap` also rebuild the stored structured-effect catalogue used by the Simulation Forge.

### Bootstrap the app for first run

```bash
python -m canoptek_calculator.cli bootstrap
```

### Run the web server

```bash
python -m canoptek_calculator.cli serve
```

## Environment variables

Copy `.env.example` if you want local overrides.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/canoptek.sqlite3` | SQLAlchemy connection string |
| `FIXTURES_DIR` | `fixtures/wahapedia/wh40k10ed` | Where downloaded CSVs are stored |
| `AUTO_SYNC_ON_STARTUP` | `false` | If `true`, the app syncs data during startup |
| `APP_ALLOWED_HOSTS` | `127.0.0.1,localhost,testserver` | Comma-separated trusted hostnames for Host header validation |
| `UNIT_EFFECT_AI_ENABLED` | `false` | Enables OpenAI-backed ability interpretation during import/sync |
| `UNIT_EFFECT_AI_MODEL` | `gpt-5-mini` | Model used for import-time ability interpretation |
| `UNIT_EFFECT_AI_BASE_URL` | `https://api.openai.com/v1` | Base URL for the OpenAI Responses API |
| `UNIT_EFFECT_AI_TIMEOUT_SECONDS` | `45` | Timeout for each AI interpretation batch |
| `UNIT_EFFECT_AI_BATCH_SIZE` | `12` | Number of abilities sent per AI interpretation batch |
| `OPENAI_API_KEY` | _(empty)_ | API key used when `UNIT_EFFECT_AI_ENABLED=true` |

## Simulation coverage

The simulation engine currently models these weapon keywords when present in Wahapedia weapon descriptions:

- `rapid fire`
- `sustained hits`
- `lethal hits`
- `twin-linked`
- `devastating wounds`
- `torrent`
- `heavy`
- `blast`
- `melta`
- `lance`
- `anti-*`
- `ignores cover`

The UI also shows any parsed rules that are not currently modeled in the engine, so you can see when a result is only partially represented.

Attached-unit abilities are interpreted at import/sync time and stored as structured effects. In the Simulation Forge, those effects start in their imported default state and can be toggled on or off per attack sequence when you need to model a conditional rule or override a bad interpretation.

### Outputs

Each simulation returns:

- expected attacks, hits, wounds, unsaved wounds, and raw damage
- Monte Carlo average wounds lost
- Monte Carlo average models slain
- kill probability
- percentile bands and a wounds-lost histogram

## API overview

### Health

```http
GET /api/health
```

### Dashboard stats

```http
GET /api/dashboard
```

### List factions

```http
GET /api/factions
```

### List datasheets

```http
GET /api/datasheets
```

Query parameters:

- `search`
- `faction_id`
- `limit`

### Datasheet detail

```http
GET /api/datasheets/{datasheet_id}
```

### Refresh Wahapedia data

```http
POST /api/sync
```

### Army list endpoints

```http
GET    /api/army-lists
POST   /api/army-lists
GET    /api/army-lists/{army_list_id}
PATCH  /api/army-lists/{army_list_id}
DELETE /api/army-lists/{army_list_id}
POST   /api/army-lists/{army_list_id}/entries
PATCH  /api/army-lists/{army_list_id}/entries/{entry_id}
DELETE /api/army-lists/{army_list_id}/entries/{entry_id}
```

### Run a simulation

```http
POST /api/simulate
```

Example payload:

```json
{
  "attacker_weapon_id": 1,
  "attacker_models": 10,
  "defender_mode": "datasheet",
  "defender_model_id": 2,
  "target_model_count": 5,
  "half_range": true,
  "trials": 5000
}
```

## Roster workflow

Use the **Roster Foundry** panel in the main UI to:

- create a named army list for a single faction
- add saved units with datasheet, model line, unit size, quantity, notes, and tracked points
- edit or remove saved units later
- load a saved unit into the attacker or defender side of the simulation form with one click

Saved army lists are kept in the application database and survive Wahapedia refreshes. If a future data import can no longer resolve a saved datasheet or model line, the UI keeps the roster entry and flags it as stale instead of silently deleting it.

## Quality checks

### Run tests

```bash
python -m pytest
```

### Run linting

```bash
python -m ruff check .
python -m ruff format .
```

## Notes on Wahapedia data

- This app is intentionally scoped to Warhammer 40,000 10th edition only
- The downloader reads Wahapedia's published export workbook to discover CSV links instead of hardcoding them
- The imported CSV data is third-party content; this project stores the downloaded files in `fixtures/` for repeatable imports and local inspection

## Attribution

When you publish work based on this dataset, attribute Wahapedia appropriately.
