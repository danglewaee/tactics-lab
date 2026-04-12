# Data Strategy

## Decision

Tactics Lab should not depend on one scraped website.

The first version should use this data model:
- primary data source: open event data
- secondary context sources: public official stats and football references
- qualitative sources: public tactical writing used for framing, not copied as data

This gives the project a clean legal and technical foundation while keeping the tactical analysis credible.

## Source Roles

### 1. StatsBomb Open Data

Role:
- primary source for V1 tactical analysis

Use it for:
- match events
- pass and carry locations
- pressures
- shots
- lineups
- competitions and matches
- selected freeze-frame style context when available

Why:
- it is event-level data, so it supports tactical questions directly
- it is suitable for building maps, metrics, and match reports
- it lets the project compute its own conclusions instead of only repeating public tables

Limit:
- Manchester United coverage may be incomplete depending on the available open competitions
- Portugal coverage is more practical for early tournament/event-data work

Implementation note:
- keep the provider layer generic so a richer paid or private data source can be added later

### 2. Premier League / Opta-Style Public Stats

Role:
- secondary benchmark and context layer

Use it for:
- sanity-checking player/team trends
- explaining familiar public metrics such as key passes, big chances created, chances created, duels won, recoveries, tackles, and interceptions
- supporting portfolio storytelling around Manchester United

Do not use it for:
- the core tactical engine
- event-level calculations
- automated scraping without permission

Why:
- these stats are useful and recognizable
- they are usually aggregated, not raw event streams
- they do not directly reveal team shape, pass networks, regain chains, or possession phases

Important naming:
- the data ecosystem behind many public football stats is commonly known through Opta, now part of Stats Perform

### 3. Transfermarkt

Role:
- player, squad, contract, transfer, and market-value context

Use it for:
- linking player identity pages
- manual context around age, contract, transfer history, and market value
- curated position frequency, such as how often a player appears at CM, AM, RW, ST, or full-back roles
- role versatility analysis, especially for players like Bruno Fernandes or Portugal attackers who can appear in multiple zones
- future scouting module context

Do not use it for:
- tactical analysis
- event metrics
- automated scraping as a project dependency

Why:
- Transfermarkt is strong for market context, not tactical event data
- relying on scraped market pages would make the project fragile
- market value is a different product question from build-up and pressing analysis

Position frequency policy:
- position frequency is valuable and should be supported
- ingest it only as curated/manual context unless there is an explicitly permitted data source
- store source URLs and snapshot dates for auditability
- use it to enrich player pages and role analysis, not to prove match-level tactical claims

### 4. Public Tactical Analysis

Role:
- qualitative inspiration and validation

Use it for:
- naming tactical concepts
- comparing whether the app's output matches human tactical interpretation
- building report templates and tactical vocabulary

Examples:
- The Analyst
- The Coaches' Voice
- Spielverlagerung
- public club or federation match reports when available

Do not use it for:
- copying conclusions directly into generated reports
- training an insight model without permission
- replacing the project's own computed evidence

## V1 Data Stack

V1 should be built around this pipeline:

1. Ingest open event data.
2. Normalize matches, teams, players, lineups, and events.
3. Compute tactical metrics from coordinates and event sequences.
4. Store metrics in `team_match_metrics` and `player_match_metrics`.
5. Join curated player context such as position frequency when showing player roles.
6. Generate rule-based tactical takeaways with evidence keys.
7. Render maps, networks, and summaries in the UI.

## Core Tactical Metrics And Data Requirements

### Build-Up Lane Split

Needs:
- pass/carry start locations
- possession or sequence context
- team direction normalization

Output:
- left, center, and right build-up share

### Progressive Passes

Needs:
- pass start and end locations
- successful pass outcome

Output:
- progressive pass count
- player leaders
- map of progression routes

### Field Tilt

Needs:
- final-third touches or actions
- team action counts

Output:
- territorial control share

### Regain Zones

Needs:
- possession changes
- defensive actions
- action coordinates

Output:
- high, middle, and deep regain counts

### Pass Network

Needs:
- completed pass events
- passer and recipient
- average player locations

Output:
- nodes for players
- edges for passing links
- centrality-style influence metrics

## Why This Is The Right Foundation

This project should be judged on whether it can produce tactical conclusions from evidence.

The strongest foundation is therefore not a market database or public stat table. It is event-level data that lets the app compute:
- where actions happened
- who connected play
- how the ball moved
- where possession was regained
- how patterns changed across matches

## Source Policy

Tactics Lab should follow these rules:
- prefer open or explicitly licensed datasets
- cite every external source used in docs or UI
- do not make scraping a core dependency
- separate raw provider data from derived metrics
- keep provider-specific fields inside `raw_event` and normalized fields in first-class columns

This keeps the project portfolio-safe and easier to extend.

## Source References

- [StatsBomb Open Data](https://github.com/statsbomb/open-data): open football event data, including competitions, matches, events, lineups, and selected 360 files.
- [Premier League Stats Centre](https://www.premierleague.com/en/stats): public official Premier League player and club stat tables.
- [Stats Perform Opta](https://www.statsperform.com/opta/): commercial Opta data feeds, APIs, and advanced football data products.
- [Transfermarkt Terms of Use](https://www.transfermarkt.com/intern/anb): terms that prohibit automated bots, spiders, screen scraping, and AI training use of digital content.
- [football-data.org](https://www.football-data.org/): machine-readable football API for fixtures, tables, squads, lineups, and match metadata; useful as context, not tactical event data.
