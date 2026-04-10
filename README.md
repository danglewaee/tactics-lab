# Tactics Lab

`Tactics Lab` is a football analysis project built around a clear thesis: explain how teams build up, press, and control space instead of just showing surface-level stats.

The portfolio angle is intentionally personal:
- club lens: Manchester United
- national team lens: Portugal
- tactical lens: build-up structure, pressing behavior, territorial control

## MVP Thesis

The first version answers questions like:
- How does a team progress the ball from the first phase?
- Which side of the pitch does build-up favor?
- Where does a team regain possession after losing the ball?
- How aggressive or passive is the press?
- Which players anchor the passing network?

## Initial Stack

- frontend: `Next.js`
- API: `FastAPI`
- database: `Postgres`
- ETL and metrics: `Python`
- charts: `ECharts` or `D3`
- data source target: `StatsBomb`-style event data

## Workspace Layout

- `apps/web`: frontend application
- `services/api`: read API for the UI
- `jobs/etl`: ingestion and metric computation jobs
- `db/schema`: database DDL
- `docs`: product and architecture documents
- `data`: local raw/processed data notes

## What Exists Now

This repository currently contains the project foundation:
- MVP and product spec
- folder ownership and architecture notes
- initial relational schema for matches, events, lineups, metrics, and reports

## Recommended Build Order

1. Load one open dataset slice and validate the schema.
2. Compute a first batch of team/match tactical metrics.
3. Expose match and team endpoints from the API.
4. Build the first `Match Page` and `Team Page`.
5. Add auto-generated tactical takeaways.

Start with [docs/MVP_SPEC.md](/D:/CODE/Projects/Football/docs/MVP_SPEC.md) and [db/schema/001_init.sql](/D:/CODE/Projects/Football/db/schema/001_init.sql).
