from __future__ import annotations

from typing import Any

from metrics.team_match import FINAL_THIRD_START_X, is_completed_pass, is_numeric_value, is_open_play_event

PROGRESSIVE_CARRY_DISTANCE = 10.0
HIGH_REGAIN_EVENT_TYPES = {"Ball Recovery", "Interception"}


def filter_player_events(events: list[dict[str, object]], player_id: int | str) -> list[dict[str, object]]:
    player_key = str(player_id)
    return [event for event in events if str(event.get("player_id")) == player_key]


def is_progressive_carry(event: dict[str, object]) -> bool:
    if event.get("event_type") != "Carry" or not is_open_play_event(event):
        return False

    x_start = event.get("x_start")
    x_end = event.get("x_end")
    if not is_numeric_value(x_start) or not is_numeric_value(x_end):
        return False
    return (x_end - x_start) >= PROGRESSIVE_CARRY_DISTANCE


def progressive_carry_count(events: list[dict[str, object]]) -> int:
    return sum(1 for event in events if is_progressive_carry(event))


def pressure_count(events: list[dict[str, object]]) -> int:
    return sum(1 for event in events if event.get("event_type") == "Pressure" and is_open_play_event(event))


def passes_received_count(events: list[dict[str, object]], player_id: int | str) -> int:
    player_key = str(player_id)
    count = 0
    for event in events:
        if event.get("event_type") != "Pass" or not is_open_play_event(event) or not is_completed_pass(event):
            continue
        if str(event.get("pass_recipient_player_id")) == player_key:
            count += 1
    return count


def player_high_regain_count(events: list[dict[str, object]], player_id: int | str, team_id: int | str) -> int:
    player_key = str(player_id)
    team_key = str(team_id)
    previous_team_key: str | None = None
    count = 0

    for event in events:
        event_team_key = str(event.get("team_id")) if event.get("team_id") is not None else None
        if event_team_key != team_key:
            if event_team_key is not None:
                previous_team_key = event_team_key
            continue

        if str(event.get("player_id")) != player_key:
            previous_team_key = event_team_key
            continue
        if event.get("event_type") not in HIGH_REGAIN_EVENT_TYPES or not is_open_play_event(event):
            previous_team_key = event_team_key
            continue
        if previous_team_key in (None, team_key):
            previous_team_key = event_team_key
            continue

        x_start = event.get("x_start")
        if is_numeric_value(x_start) and x_start >= FINAL_THIRD_START_X:
            count += 1
        previous_team_key = event_team_key

    return count


def normalize_minutes_played(lineup_row: dict[str, Any], match_end_minute: int) -> int:
    start_minute = int(lineup_row.get("start_minute") or 0)
    raw_end_minute = int(lineup_row.get("end_minute") or match_end_minute)
    end_minute = min(raw_end_minute, match_end_minute)
    if end_minute < start_minute:
        return 0
    return end_minute - start_minute


def compute_player_match_metrics(
    events: list[dict[str, object]],
    lineup_row: dict[str, Any],
    match_end_minute: int,
) -> dict[str, float]:
    player_id = lineup_row["player_id"]
    team_id = lineup_row["team_id"]
    player_events = filter_player_events(events, player_id)
    minutes_played = normalize_minutes_played(lineup_row, match_end_minute)

    return {
        "minutes_played": float(minutes_played),
        "progressive_passes": float(sum(1 for event in player_events if event.get("event_type") == "Pass" and is_completed_pass(event) and is_open_play_event(event) and is_numeric_value(event.get("x_start")) and is_numeric_value(event.get("x_end")) and (event.get("x_end") - event.get("x_start")) >= 10)),
        "progressive_carries": float(progressive_carry_count(player_events)),
        "passes_received": float(passes_received_count(events, player_id)),
        "pressures": float(pressure_count(player_events)),
        "high_regains": float(player_high_regain_count(events, player_id, team_id)),
    }
