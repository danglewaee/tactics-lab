# Tactics Lab MVP Spec

## 1. Product Goal

Build a football tactics analysis app that turns event data into readable tactical insight.

Purpose statement:

> Tactics Lab is a football tactics intelligence platform focused on Manchester United and Portugal, designed to turn event-level match data into clear tactical insights about build-up patterns, pressing behavior, territorial control, and player influence.

The product should feel opinionated, not generic:
- it should reflect a real fan perspective
- it should focus on team identity and game patterns
- it should prioritize interpretation over stat dumping

## 2. Project Thesis

The MVP focuses on:
- Manchester United as the personal club lens
- Portugal as the national team lens
- build-up and pressing as the tactical core

This gives the project a strong personal narrative for a portfolio while keeping the first implementation bounded.

## 3. Primary Questions

The MVP should answer:
- Does the team build through the center or lean to one side?
- How direct or patient is the first phase?
- Where does the team win the ball back?
- How high does the team press?
- Which players are the main connectors in possession?
- How does the tactical story change from match to match?

## 4. Users

Primary user:
- a football fan who wants tactical explanations, not only final scores or raw tables

Secondary user:
- a recruiter or interviewer who should quickly see product sense, data design, and analytical depth

## 5. MVP Scope

### In scope

- seed the platform with MU and Portugal as the editorial focus
- ingest event-level match data
- support team and match pages
- compute a first set of tactical metrics
- render tactical visualizations
- generate short rule-based tactical summaries

### Out of scope

- live match ingestion
- full player scouting system
- computer vision from video
- full league coverage
- prediction as the main product surface

## 6. Core Pages

### Home

Purpose:
- explain the thesis of the project
- highlight MU and Portugal
- surface featured tactical reports

### Team Page

Purpose:
- show a team identity view across selected matches

Key blocks:
- build-up profile
- pressing profile
- field tilt and territorial control
- progressive passing leaders
- team tactical summary

### Match Page

Purpose:
- explain how one match played out tactically

Key blocks:
- passing network
- zone occupation heatmap
- regain zones
- progressive pass map
- team-by-team comparison
- auto-generated tactical takeaways

### Compare View

Purpose:
- compare MU vs Portugal, or one team across two matches

Key blocks:
- metric deltas
- build-up lane split comparison
- regain height comparison
- possession connector comparison

## 7. Tactical Metrics For V1

The first release should include a small set of metrics that are explainable and visually meaningful.

### Team metrics

- `field_tilt`
  share of final-third territory or actions controlled by a team

- `build_up_lane_split`
  percentage of early progression actions through left, center, and right lanes

- `progressive_passes`
  total and per-90 progressive passes

- `verticality_index`
  how directly possessions move toward goal

- `high_regains`
  regains in the attacking third or high press zones

- `middle_regains`
  regains in the middle third

- `counterpress_regains`
  regains shortly after losing possession

- `pass_network_centrality`
  identifies the possession hubs

### Player metrics

- progressive passes
- progressive carries
- receptions between lines
- regains
- pressures
- network centrality

## 8. Insight Generation

The first insight layer should be rule-based, not LLM-first.

Example outputs:
- "Portugal progressed mainly down the left in the first phase, with the left lane producing 48% of early progression actions."
- "Manchester United regained possession unusually high, suggesting a more aggressive press than its baseline."
- "Bruno Fernandes and the right-back formed the main possession bridge in this match."

This is important because it creates an explainable path from raw events to insight.

## 9. Data Strategy

### Initial provider assumption

Use an event-data provider with a structure similar to `StatsBomb`.

Primary V1 data source:
- open event data that includes coordinates, event types, teams, players, lineups, and match metadata

Secondary context sources:
- Premier League / Opta-style public stat tables for familiar aggregated metrics
- Transfermarkt for market and squad context only
- public tactical writing for vocabulary and qualitative validation

### Important constraint

Open-data coverage for MU may be partial depending on provider and competition selection.

Practical approach:
- make the data layer provider-aware
- start with Portugal matches and any available MU sample
- keep the UI branded around the MU + Portugal editorial thesis
- expand to richer club coverage later if a different provider is added

This is an implementation assumption, not a hard product limitation.

Full data-source policy:
- see [DATA_STRATEGY.md](/D:/CODE/Projects/Football/docs/DATA_STRATEGY.md)

## 10. Engineering Goals

The MVP should demonstrate:
- clean ETL boundaries
- a normalized event schema
- reproducible metric computation
- API design for analytics reads
- strong visual communication in the frontend

## 11. Folder Responsibilities

- `apps/web`
  presentation, routing, chart composition, report UX

- `services/api`
  match/team/report endpoints, filtering, typed responses

- `jobs/etl`
  raw ingestion, normalization, metric computation, report generation

- `db/schema`
  relational schema and later migrations

## 12. Milestones

### Milestone 1

- ingest one dataset slice
- populate competitions, teams, players, matches, lineups, events

### Milestone 2

- compute first metrics: field tilt, lane split, progressive passes, regain zones

### Milestone 3

- ship team page and match page

### Milestone 4

- add compare view and rule-based tactical summaries

## 13. Success Criteria

The MVP is successful if:
- a user can open a MU or Portugal match and understand the tactical shape in under 60 seconds
- the app surfaces at least 3 non-trivial tactical takeaways from event data
- the architecture is clean enough to extend into scouting or computer vision later
