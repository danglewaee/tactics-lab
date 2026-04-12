from __future__ import annotations

import csv
from pathlib import Path


NUMERIC_FIELDS = {
    "appearances": int,
    "starts": int,
    "minutes_played": int,
    "goals": int,
    "assists": int,
    "position_share": float,
}


def _coerce_value(key: str, value: str) -> object:
    value = value.strip()
    if value == "":
        return None

    converter = NUMERIC_FIELDS.get(key)
    if converter is None:
        return value
    return converter(value)


def read_player_position_profiles(csv_path: str | Path) -> list[dict[str, object]]:
    path = Path(csv_path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {key: _coerce_value(key, value or "") for key, value in row.items()}
            for row in reader
        ]
