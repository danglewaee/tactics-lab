# API Service

`FastAPI` service for:
- team reads
- match reads
- metric endpoints
- tactical report endpoints

Keep analytics logic out of request handlers. Heavy computation should live in `jobs/etl`.

## Bootstrap Endpoints

- `GET /`
- `GET /api/health`
- `GET /api/teams`
- `GET /api/teams/{team_slug}`
- `GET /api/teams/{team_slug}/matches`
- `GET /api/matches/{match_id}`
- `GET /api/matches/{match_id}/network`
- `GET /api/matches/{match_id}/reports`

The current responses are editorial placeholders for `Manchester United` and `Portugal`. They establish the API shape before the database-backed implementation lands.

