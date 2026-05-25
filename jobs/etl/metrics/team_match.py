from __future__ import annotations

from collections import Counter
from decimal import Decimal

BUILD_UP_MAX_START_X = 60.0
FINAL_THIRD_START_X = 80.0
BUILD_UP_ACTIONS_PER_POSSESSION = 3
EXCLUDED_SET_PIECE_PATTERNS = {"From Corner", "From Free Kick", "From Penalty", "From Throw In"}
TERRITORIAL_EVENT_TYPES = {"Pass", "Carry", "Dribble", "Shot"}
HIGH_REGAIN_EVENT_TYPES = {"Ball Recovery", "Interception"}


def is_progressive_pass(event: dict[str, object]) -> bool:
    if not is_completed_pass(event) or not is_open_play_event(event):
        return False

    x_start = event.get("x_start")
    x_end = event.get("x_end")
    if not is_numeric_value(x_start) or not is_numeric_value(x_end):
        return False
    return (x_end - x_start) >= 10


def progressive_pass_count(events: list[dict[str, object]]) -> int:
    return sum(1 for event in events if is_progressive_pass(event))


def filter_team_events(events: list[dict[str, object]], team_id: int | str) -> list[dict[str, object]]:
    team_key = str(team_id)
    return [event for event in events if str(event.get("team_id")) == team_key]


def build_up_lane_share(events: list[dict[str, object]]) -> dict[str, float]:
    lane_counts: Counter[str] = Counter()
    possession_action_counts: dict[str, int] = {}

    for event in events:
        if not is_build_up_action(event):
            continue

        possession_key = possession_event_key(event)
        action_count = possession_action_counts.get(possession_key, 0)
        if action_count >= BUILD_UP_ACTIONS_PER_POSSESSION:
            continue
        possession_action_counts[possession_key] = action_count + 1

        lane = lane_for_event(event)
        if lane is None:
            continue
        lane_counts[lane] += 1

    total = sum(lane_counts.values())
    if total == 0:
        return {"left": 0.0, "center": 0.0, "right": 0.0}

    return {
        "left": round(lane_counts["left"] / total, 4),
        "center": round(lane_counts["center"] / total, 4),
        "right": round(lane_counts["right"] / total, 4),
    }


def field_tilt(events: list[dict[str, object]], team_id: int | str) -> float:
    team_key = str(team_id)
    team_final_third_actions = 0
    total_final_third_actions = 0

    for event in events:
        if not is_territorial_action(event):
            continue
        x_start = event.get("x_start")
        if not is_numeric_value(x_start):
            continue
        if x_start < FINAL_THIRD_START_X:
            continue
        total_final_third_actions += 1
        if str(event.get("team_id")) == team_key:
            team_final_third_actions += 1

    if total_final_third_actions == 0:
        return 0.0
    return round(team_final_third_actions / total_final_third_actions, 4)


def high_regain_count(events: list[dict[str, object]], team_id: int | str) -> int:
    team_key = str(team_id)
    count = 0
    previous_team_key: str | None = None

    for event in events:
        event_team_key = str(event.get("team_id")) if event.get("team_id") is not None else None
        if event_team_key != team_key:
            if event_team_key is not None:
                previous_team_key = event_team_key
            continue

        if not is_open_play_event(event):
            previous_team_key = event_team_key
            continue
        if event.get("event_type") not in HIGH_REGAIN_EVENT_TYPES:
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


def compute_team_match_metrics(events: list[dict[str, object]], team_id: int | str) -> dict[str, float]:
    team_events = filter_team_events(events, team_id)
    lane_share = build_up_lane_share(team_events)

    return {
        "progressive_passes": float(progressive_pass_count(team_events)),
        "left_lane_build_up_share": lane_share["left"],
        "center_lane_build_up_share": lane_share["center"],
        "right_lane_build_up_share": lane_share["right"],
        "field_tilt": field_tilt(events, team_id),
        "high_regains": float(high_regain_count(events, team_id)),
    }


def is_open_play_event(event: dict[str, object]) -> bool:
    play_pattern = event.get("play_pattern")
    if play_pattern is None:
        return True
    if not isinstance(play_pattern, str):
        return False
    return play_pattern not in EXCLUDED_SET_PIECE_PATTERNS


def is_completed_pass(event: dict[str, object]) -> bool:
    if event.get("event_type") != "Pass":
        return False

    outcome = event.get("outcome")
    return outcome in (None, "", "Complete", "Success", "Success In Play", "Won")


def is_build_up_action(event: dict[str, object]) -> bool:
    if not is_open_play_event(event):
        return False
    if event.get("event_type") not in {"Pass", "Carry"}:
        return False
    if event.get("event_type") == "Pass" and not is_completed_pass(event):
        return False

    x_start = event.get("x_start")
    x_end = event.get("x_end")
    if not is_numeric_value(x_start) or not is_numeric_value(x_end):
        return False
    if x_start > BUILD_UP_MAX_START_X:
        return False
    return x_end > x_start


def is_territorial_action(event: dict[str, object]) -> bool:
    return is_open_play_event(event) and event.get("event_type") in TERRITORIAL_EVENT_TYPES


def possession_event_key(event: dict[str, object]) -> str:
    possession_id = event.get("possession_id")
    if possession_id is not None:
        return f"possession:{possession_id}"
    index_in_match = event.get("index_in_match")
    if index_in_match is not None:
        return f"index:{index_in_match}"
    return "fallback"


def lane_for_event(event: dict[str, object]) -> str | None:
    y_start = event.get("y_start")
    if not is_numeric_value(y_start):
        return None

    if y_start < 26.67:
        return "left"
    if y_start <= 53.33:
        return "center"
    return "right"


def is_numeric_value(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)
