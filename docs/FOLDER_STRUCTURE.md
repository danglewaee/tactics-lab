# Folder Structure

## Target Layout

```text
Football/
|-- apps/
|   `-- web/
|       |-- app/
|       |-- components/
|       |-- lib/
|       `-- styles/
|-- services/
|   `-- api/
|       |-- app/
|       |-- routers/
|       |-- services/
|       |-- schemas/
|       `-- tests/
|-- jobs/
|   `-- etl/
|       |-- ingest/
|       |-- transform/
|       |-- metrics/
|       `-- reports/
|-- db/
|   `-- schema/
|-- data/
|   |-- raw/
|   `-- processed/
`-- docs/
```

## Ownership

### `apps/web`

- renders the product
- owns route structure and chart composition
- consumes read-only API responses

### `services/api`

- serves team, match, metric, and report endpoints
- translates DB models into frontend-friendly payloads
- should stay thin and avoid embedding ETL logic

### `jobs/etl`

- imports raw provider files
- normalizes provider payloads into the shared schema
- computes derived tactical metrics
- generates rule-based summaries for reports

### `db/schema`

- holds the base relational model
- later can grow into versioned migrations

### `data`

- local development scratch space for raw and processed datasets
- should not be committed when files become large

## Suggested First Endpoints

- `GET /health`
- `GET /teams`
- `GET /teams/{teamId}`
- `GET /teams/{teamId}/matches`
- `GET /matches/{matchId}`
- `GET /matches/{matchId}/network`
- `GET /matches/{matchId}/reports`

## Suggested First Jobs

- `ingest_competitions`
- `ingest_matches`
- `ingest_lineups`
- `ingest_events`
- `compute_team_match_metrics`
- `compute_player_match_metrics`
- `generate_tactical_report`
