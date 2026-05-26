from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


WINDOW_RATE_METRICS = {
    "progressive_passes": "progressive_passes_per90",
    "progressive_carries": "progressive_carries_per90",
    "passes_received": "passes_received_per90",
    "pressures": "pressures_per90",
    "high_regains": "high_regains_per90",
}


@dataclass(slots=True)
class PlayerWindowMetric:
    player_id: int
    team_id: int
    competition_id: int | None
    season_id: int | None
    window_type: str
    window_key: str
    metric_key: str
    metric_value: float
    match_count: int
    minutes_played_total: int
    window_start_date: date | None
    window_end_date: date | None
    metric_context: dict[str, Any]


@dataclass(slots=True)
class _WindowBucket:
    player_id: int
    team_id: int
    competition_id: int | None
    season_id: int | None
    window_type: str
    window_key: str
    metric_totals: dict[str, float]
    match_ids: set[int] | None = None
    window_start_date: date | None = None
    window_end_date: date | None = None

    def __post_init__(self) -> None:
        if self.match_ids is None:
            self.match_ids = set()
        if self.metric_totals is None:
            self.metric_totals = {}

    def add(self, match_id: int, match_date: date | None, metric_key: str, metric_value: float) -> None:
        self.metric_totals[metric_key] = self.metric_totals.get(metric_key, 0.0) + metric_value
        self.match_ids.add(match_id)
        if match_date is not None:
            if self.window_start_date is None or match_date < self.window_start_date:
                self.window_start_date = match_date
            if self.window_end_date is None or match_date > self.window_end_date:
                self.window_end_date = match_date

    def to_metrics(self) -> list[PlayerWindowMetric]:
        minutes_played_total = int(round(self.metric_totals.get("minutes_played", 0.0)))
        match_count = len(self.match_ids)
        metrics: list[PlayerWindowMetric] = [
            PlayerWindowMetric(
                player_id=self.player_id,
                team_id=self.team_id,
                competition_id=self.competition_id,
                season_id=self.season_id,
                window_type=self.window_type,
                window_key=self.window_key,
                metric_key="minutes_played",
                metric_value=float(minutes_played_total),
                match_count=match_count,
                minutes_played_total=minutes_played_total,
                window_start_date=self.window_start_date,
                window_end_date=self.window_end_date,
                metric_context={
                    "aggregation": "sum",
                    "input_metric_key": "minutes_played",
                    "source_table": "player_match_metrics",
                    "window_type": self.window_type,
                },
            )
        ]

        for input_metric_key, output_metric_key in WINDOW_RATE_METRICS.items():
            total = self.metric_totals.get(input_metric_key, 0.0)
            metric_value = 0.0 if minutes_played_total == 0 else round((total / minutes_played_total) * 90, 4)
            metrics.append(
                PlayerWindowMetric(
                    player_id=self.player_id,
                    team_id=self.team_id,
                    competition_id=self.competition_id,
                    season_id=self.season_id,
                    window_type=self.window_type,
                    window_key=self.window_key,
                    metric_key=output_metric_key,
                    metric_value=metric_value,
                    match_count=match_count,
                    minutes_played_total=minutes_played_total,
                    window_start_date=self.window_start_date,
                    window_end_date=self.window_end_date,
                    metric_context={
                        "aggregation": "per90_from_sum",
                        "input_metric_key": input_metric_key,
                        "source_table": "player_match_metrics",
                        "window_type": self.window_type,
                    },
                )
            )

        return metrics


def aggregate_player_window_metrics(rows: list[dict[str, Any]]) -> list[PlayerWindowMetric]:
    buckets: dict[tuple[int, int, int | None, int | None, str, str], _WindowBucket] = {}

    for row in rows:
        player_id = int(row["player_id"])
        team_id = int(row["team_id"])
        match_id = int(row["match_id"])
        competition_id = int(row["competition_id"]) if row.get("competition_id") is not None else None
        season_id = int(row["season_id"]) if row.get("season_id") is not None else None
        metric_key = str(row["metric_key"])
        metric_value = numeric_as_float(row.get("metric_value"))
        match_date = normalize_date(row.get("match_date"))

        if metric_value is None:
            continue

        for window_type, window_key, scoped_competition_id, scoped_season_id in build_windows(
            player_id=player_id,
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
        ):
            bucket_key = (
                player_id,
                team_id,
                scoped_competition_id,
                scoped_season_id,
                window_type,
                window_key,
            )
            bucket = buckets.get(bucket_key)
            if bucket is None:
                bucket = _WindowBucket(
                    player_id=player_id,
                    team_id=team_id,
                    competition_id=scoped_competition_id,
                    season_id=scoped_season_id,
                    window_type=window_type,
                    window_key=window_key,
                    metric_totals={},
                )
                buckets[bucket_key] = bucket
            bucket.add(match_id=match_id, match_date=match_date, metric_key=metric_key, metric_value=metric_value)

    metrics: list[PlayerWindowMetric] = []
    for bucket in buckets.values():
        metrics.extend(bucket.to_metrics())

    return sorted(
        metrics,
        key=lambda item: (
            item.player_id,
            item.team_id,
            item.window_type,
            item.window_key,
            item.metric_key,
        ),
    )


def build_windows(
    player_id: int,
    team_id: int,
    competition_id: int | None,
    season_id: int | None,
) -> list[tuple[str, str, int | None, int | None]]:
    windows = [
        ("all_matches", f"player:{player_id}:team:{team_id}:all_matches", None, None),
    ]

    if competition_id is not None:
        windows.append(
            (
                "competition",
                f"player:{player_id}:team:{team_id}:competition:{competition_id}",
                competition_id,
                None,
            )
        )

    if season_id is not None:
        windows.append(
            (
                "season",
                f"player:{player_id}:team:{team_id}:season:{season_id}",
                None,
                season_id,
            )
        )

    if competition_id is not None and season_id is not None:
        windows.append(
            (
                "competition_season",
                f"player:{player_id}:team:{team_id}:competition:{competition_id}:season:{season_id}",
                competition_id,
                season_id,
            )
        )

    return windows


def normalize_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return None


def numeric_as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return None
