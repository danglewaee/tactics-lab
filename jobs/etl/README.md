# ETL Jobs

Responsibilities:
- provider ingestion
- schema normalization
- metric computation
- report generation

The first jobs should assume event-style data and write into the schema defined in `db/schema/001_init.sql`.

## Bootstrap CLI

Two simple commands are available once Python dependencies are installed:

- `python jobs/etl/main.py manifest`
- `python jobs/etl/main.py plan`
- `python jobs/etl/main.py scan-statsbomb --raw-dir data/raw/statsbomb`
- `python jobs/etl/main.py ingest-statsbomb --raw-dir data/raw/statsbomb --limit-matches 3`

The initial implementation is intentionally light:
- provider manifest definition
- event normalization helpers
- curated player position profile reader
- StatsBomb Open Data scan and ingest commands
- first metric primitives for progressive passes and lane split
- rule-based takeaway generation

Manual player context starts from `data/manual/player_position_profiles.csv`.

## Expected StatsBomb Layout

The StatsBomb Open Data checkout can be placed at `data/raw/statsbomb`.

Supported layouts:
- `data/raw/statsbomb/data/competitions.json`
- `data/raw/statsbomb/competitions.json`

The ingest command expects the standard `matches`, `lineups`, and `events` folders next to `competitions.json`.
