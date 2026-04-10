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

The initial implementation is intentionally light:
- provider manifest definition
- event normalization helpers
- first metric primitives for progressive passes and lane split
- rule-based takeaway generation

