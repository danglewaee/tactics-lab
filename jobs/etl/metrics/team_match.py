from __future__ import annotations

from collections import Counter


def is_progressive_pass(event: dict[str, object]) -> bool:
    if event.get("event_type") != "Pass":
        return False

    x_start = event.get("x_start")
    x_end = event.get("x_end")
    if not isinstance(x_start, (int, float)) or not isinstance(x_end, (int, float)):
        return False
    return (x_end - x_start) >= 10


def progressive_pass_count(events: list[dict[str, object]]) -> int:
    return sum(1 for event in events if is_progressive_pass(event))


def build_up_lane_share(events: list[dict[str, object]]) -> dict[str, float]:
    lane_counts: Counter[str] = Counter()

    for event in events:
        if event.get("event_type") != "Pass":
            continue

        y_start = event.get("y_start")
        if not isinstance(y_start, (int, float)):
            continue

        if y_start < 26.67:
            lane_counts["left"] += 1
        elif y_start <= 53.33:
            lane_counts["center"] += 1
        else:
            lane_counts["right"] += 1

    total = sum(lane_counts.values())
    if total == 0:
        return {"left": 0.0, "center": 0.0, "right": 0.0}

    return {
        "left": round(lane_counts["left"] / total, 4),
        "center": round(lane_counts["center"] / total, 4),
        "right": round(lane_counts["right"] / total, 4),
    }

