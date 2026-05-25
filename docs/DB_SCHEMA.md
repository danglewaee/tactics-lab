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

### `player_position_profiles`

Stores curated position frequency context for players.

Examples:
- Bruno Fernandes appearing as AM, CM, or RW
- a Portugal forward splitting minutes between LW and ST
- a full-back profile showing LB/RB flexibility

This table is context enrichment. It should not replace event-level tactical evidence.

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

### `team_window_metrics`

Stores one row per metric per team per historical window.

Initial window types:
- `all_matches`
- `competition`
- `season`
- `competition_season`

Examples:
- Manchester United style profile across all ingested matches
- Portugal style profile inside one tournament
- a season-specific build-up profile for one team

This table is the first historical aggregation layer above `team_match_metrics`.

### `tactical_reports`

Stores generated insight blocks for:
- a single match
- a rolling team window
- a comparison view

## Why Metrics Are Stored Long-Form

`team_match_metrics`, `player_match_metrics`, and `team_window_metrics` use `metric_key` + `metric_value` instead of wide fixed columns.

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

Window level:
- `field_tilt`
- `progressive_passes`
- `high_regains`
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
- team style profile aggregated across a season or competition
- player contribution leaders across a match sample
- position frequency context for a selected player
- generated tactical summary for a match page

## Future Extensions

Later, the schema can be extended with:
- possession-phase tables
- tracking or freeze-frame tables
- embeddings for scouting and similarity search
- materialized views for team windows and rolling averages

The initial SQL file lives at [db/schema/001_init.sql](/D:/CODE/Projects/Football/db/schema/001_init.sql).
