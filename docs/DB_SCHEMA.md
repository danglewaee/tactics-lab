# Database Schema Notes

## Design Goal

The schema is optimized for:
- event-level football data
- reproducible metric computation
- serving match and team analytics to the frontend

It separates:
- raw-ish provider entities
- derived tactical metrics
- generated tactical reports

## Core Tables

### `providers`

Defines the upstream source. This keeps the app provider-aware from the start.

### `ingestion_runs`

Tracks ETL activity:
- what was loaded
- from where
- whether it succeeded

### `competitions` and `seasons`

Competition metadata used to organize matches and filtering.

### `teams`

Stores clubs and national teams in the same table so MU and Portugal can be queried uniformly.

### `players`

Stores player identity and lightweight profile metadata.

### `matches`

Stores fixture context:
- teams
- score
- competition
- date

### `lineups`

Stores match-specific player participation, starting status, and role context.

### `events`

The most important table.

It stores event stream data such as:
- passes
- carries
- shots
- regains
- pressures

It also keeps location fields so tactical maps can be rendered directly.

### `event_related_events`

Supports provider relationships such as:
- pass -> shot link
- duel chains
- event follow-ups

### `team_match_metrics`

Stores one row per metric per team per match.

Examples:
- `field_tilt`
- `high_regains`
- `verticality_index`
- `left_lane_build_up_share`

### `player_match_metrics`

Stores one row per metric per player per match.

Examples:
- `progressive_passes`
- `receptions_between_lines`
- `network_centrality`

### `tactical_reports`

Stores generated insight blocks for:
- a single match
- a rolling team window
- a comparison view

## Why Metrics Are Stored Long-Form

`team_match_metrics` and `player_match_metrics` use `metric_key` + `metric_value` instead of wide fixed columns.

This keeps the MVP flexible because new tactical metrics will change often while you learn what is actually useful.

## Recommended First Metric Keys

Team level:
- `field_tilt`
- `progressive_passes`
- `verticality_index`
- `high_regains`
- `middle_regains`
- `counterpress_regains`
- `left_lane_build_up_share`
- `center_lane_build_up_share`
- `right_lane_build_up_share`

Player level:
- `progressive_passes`
- `progressive_carries`
- `pressures`
- `regains`
- `network_centrality`
- `receptions_between_lines`

## Query Patterns The Schema Supports

- all matches for Portugal in a competition window
- MU match event stream ordered by `index_in_match`
- team tactical metrics for a selected match
- player contribution leaders across a match sample
- generated tactical summary for a match page

## Future Extensions

Later, the schema can be extended with:
- possession-phase tables
- tracking or freeze-frame tables
- embeddings for scouting and similarity search
- materialized views for team windows and rolling averages

The initial SQL file lives at [db/schema/001_init.sql](/D:/CODE/Projects/Football/db/schema/001_init.sql).

