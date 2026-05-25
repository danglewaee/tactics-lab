# Tactics Lab Metrics Spec

## 1. Purpose

This document defines how Tactics Lab turns event data into tactical metrics.

The rule is simple:
- event data provides the evidence
- metric definitions provide the contract
- tactical reports only say what the metric can actually support

This project should borrow the discipline of Opta-style definitions, not blindly copy vendor terminology.

## 2. Design Rules

### Evidence First

Every metric must be traceable to stored events:
- event type
- team
- player
- location
- end location where available
- match context

If a statement cannot be tied back to concrete event rules, it should not appear in a tactical report.

### Operational Definitions

Each metric must specify:
- what football question it tries to answer
- which events count
- which zone rules apply
- how the value is calculated
- what the metric cannot prove

### Naming Discipline

Tactics Lab must not overclaim.

Examples:
- `high_regains` is not the same thing as full pressing quality
- `lane_split` is not the same thing as a complete build-up model
- `field_tilt` must state whether it is a classic two-team territorial share or a simpler team-only proxy

## 3. Data Assumptions

V1 is built on `StatsBomb`-style event data.

Current assumptions:
- events are stored in provider-native pitch coordinates
- for `StatsBomb`, event x-coordinates already point toward the attacking goal of the team performing the action
- passes and carries can be analyzed from start and end locations
- event order inside a match is preserved
- the current metric pipeline does not yet isolate all set-piece or restart contexts

That means some V1 metrics are intentionally labeled as `proxy` metrics rather than final tactical measures, but V1 does not need half-by-half pitch flipping for `StatsBomb` event coordinates.

## 4. Current V1 Metrics

## `progressive_passes`

Status:
- implemented

Football question:
- how often did a team move the ball meaningfully forward by pass?

Current event rule:
- use team events where `event_type = Pass`
- require the event to be open play
- require the pass to be completed
- require numeric `x_start` and `x_end`
- count the pass if `x_end - x_start >= 10`

Formula:
- `progressive_passes = count(qualifying passes)`

Current caveats:
- still uses a simple forward-distance threshold
- does not yet segment by possession phase or match state

Planned refinement:
- optionally move to a goal-distance or percentage-based progression rule

## `build_up_lane_split`

Status:
- implemented as a first proxy

Football question:
- through which lane did a team start most of its passing actions?

Current event rule:
- use team open-play `Pass` and `Carry` events
- require positive forward progression
- require `x_start <= 60`
- take at most the first three qualifying actions per possession
- classify lane from `y_start`
- `left` if `y_start < 26.67`
- `center` if `26.67 <= y_start <= 53.33`
- `right` if `y_start > 53.33`

Formula:
- `lane_share(lane) = qualifying_first_phase_actions_started_in_lane / all_qualifying_first_phase_actions`

Current caveats:
- this is still a first-phase proxy rather than a full possession model
- it uses a fixed own-half cutoff
- it does not yet separate goalkeeper restarts from settled possession in more detail

Planned refinement:
- tune possession-entry and restart logic
- add match-state and phase filters

## `field_tilt`

Status:
- implemented as a two-team territorial share

Football question:
- how much of the final-third territorial share belonged to one team?

Current event rule:
- use open-play events with `event_type` in:
  - `Pass`
  - `Carry`
  - `Dribble`
  - `Shot`
- count only events with numeric `x_start`
- count an event as a final-third action if `x_start >= 80`

Formula:
- `field_tilt = team_final_third_actions / total_final_third_actions_both_teams`

Current caveats:
- this is a simple event-count territorial share, not a possession-sequence territorial model
- it does not yet distinguish sustained territory from brief final-third entries
- it treats all qualifying action types equally

Planned refinement:
- evaluate whether passes, touches, or possessions should be the numerator unit

## `high_regains`

Status:
- implemented as a regain-zone proxy

Football question:
- how often did a team win the ball back high up the pitch?

Current event rule:
- use open-play team events with `event_type` in:
  - `Ball Recovery`
  - `Interception`
- require the immediately preceding event to belong to the opponent
- count only events with numeric `x_start >= 80`

Formula:
- `high_regains = count(qualifying regain events)`

Current caveats:
- preceding-event ownership is still a proxy for a true turnover boundary
- does not yet isolate counterpress windows
- does not yet separate settled high regains from transition regains
- this is evidence of high ball wins, not a full pressing model

Planned refinement:
- split into `high_regains`, `middle_regains`, and `counterpress_regains`
- add time-from-loss logic for counterpress behavior

## 5. Tactical Reports

Current tactical report generation is rule-based.

Current report rules:
- if `center_lane_build_up_share >= 0.5`, say the team progressed mainly through the center
- else if `left_lane_build_up_share >= 0.45`, say the team leaned on the left lane
- else if `right_lane_build_up_share >= 0.45`, say the team favored the right lane
- if `field_tilt >= 0.6`, say the team controlled a larger share of final-third actions
- if `high_regains >= 6`, say the team recovered the ball high often enough to suggest sustained pressure
- otherwise say the team showed a balanced profile in the current metric set

Important limitation:
- these are starter rules for product wiring, not final tactical interpretation logic

## 6. Metrics Not Yet Implemented

These are part of the product direction but are not yet computed in the pipeline:
- `verticality_index`
- `middle_regains`
- `counterpress_regains`
- `pass_network_centrality`
- `progressive_carries`
- `receptions_between_lines`

They should not be presented as completed analytics until the event rules and validation logic exist.

## 7. Validation Strategy

A metric is only ready for the main product surface when it passes three checks:

1. Definition check
- the rule can be written in one paragraph without ambiguity

2. Data check
- the required source fields exist consistently in the provider feed

3. Football check
- the result passes a sanity check against match footage, public tactical analysis, or trusted benchmark tables

## 8. Reference Sources

Reference these sources for definition discipline, not for blind feature copying:
- `StatsBomb Open Data` for event structure and available fields
- `Stats Perform / Opta event definitions` for operational vocabulary
- `Opta Analyst sequence and possession writing` for possession-based metric framing
