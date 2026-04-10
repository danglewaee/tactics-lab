from __future__ import annotations


def normalize_coordinates(location: list[float] | None) -> tuple[float | None, float | None]:
    if not location or len(location) < 2:
        return None, None
    return float(location[0]), float(location[1])


def normalize_event(raw_event: dict[str, object]) -> dict[str, object]:
    x_start, y_start = normalize_coordinates(raw_event.get("location"))  # type: ignore[arg-type]
    end_location = raw_event.get("pass_end_location") or raw_event.get("carry_end_location")
    x_end, y_end = normalize_coordinates(end_location)  # type: ignore[arg-type]

    return {
        "external_id": raw_event.get("id"),
        "event_type": raw_event.get("type"),
        "minute": raw_event.get("minute", 0),
        "second": raw_event.get("second", 0),
        "x_start": x_start,
        "y_start": y_start,
        "x_end": x_end,
        "y_end": y_end,
        "under_pressure": bool(raw_event.get("under_pressure", False)),
        "counterpress": bool(raw_event.get("counterpress", False)),
    }

