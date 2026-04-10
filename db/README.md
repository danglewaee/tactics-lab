# Database Bootstrap

The local development database is provisioned through [compose.yaml](/D:/CODE/Projects/Football/compose.yaml).

## Local Flow

1. Copy `.env.example` to `.env`.
2. Run `docker compose up db`.
3. Postgres will execute every SQL file in `db/schema` on first boot.

## Current Contents

- [001_init.sql](/D:/CODE/Projects/Football/db/schema/001_init.sql): base provider, event, metric, and report tables

Later migrations can live in this directory as ordered SQL files.

