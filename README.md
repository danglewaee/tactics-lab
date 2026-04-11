# Tactics Lab

`Tactics Lab` is a football analysis project built around a clear thesis: explain how teams build up, press, and control space instead of just showing surface-level stats.

## Purpose

Tactics Lab is a football tactics intelligence platform focused on Manchester United and Portugal. It turns event-level match data into clear tactical insights about build-up patterns, pressing behavior, territorial control, and player influence.

The goal is not to clone a score app. The goal is to show how a football fan with an engineering mindset can read the game through data, visualizations, and explainable tactical reports.

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
- a bootstrap `FastAPI` service
- an ETL CLI skeleton with first metric helpers
- a local `docker compose` stack for Postgres + API
- a documented data-source strategy for event data, public stats, and tactical references

## Recommended Build Order

1. Load one open dataset slice and validate the schema.
2. Replace editorial placeholder responses with database-backed reads.
3. Compute a first batch of team/match tactical metrics.
4. Build the first `Match Page` and `Team Page`.
5. Add auto-generated tactical takeaways.

## Run The Bootstrap Stack

1. Copy `.env.example` to `.env`.
2. Start Postgres with `docker compose up db`.
3. Install API dependencies from `services/api/requirements.txt`.
4. Run the API with `uvicorn app.main:app --app-dir services/api --reload`.
5. Inspect the ETL bootstrap plan with `python jobs/etl/main.py plan`.

Start with [docs/MVP_SPEC.md](/D:/CODE/Projects/Football/docs/MVP_SPEC.md) and [db/schema/001_init.sql](/D:/CODE/Projects/Football/db/schema/001_init.sql).

Data-source decisions are documented in [docs/DATA_STRATEGY.md](/D:/CODE/Projects/Football/docs/DATA_STRATEGY.md).
