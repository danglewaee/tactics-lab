from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class TeamWindowMetric:
    team_id: int
    competition_id: int | None
    season_id: int | None
    window_type: str
    window_key: str
    metric_key: str
    metric_value: float
    match_count: int
    window_start_date: date | None
    window_end_date: date | None
    metric_context: dict[str, Any]


@dataclass(slots=True)
class _WindowBucket:
    team_id: int
    competition_id: int | None
    season_id: int | None
    window_type: str
    window_key: str
    metric_key: str
    metric_sum: float = 0.0
    metric_count: int = 0
    match_ids: set[int] | None = None
    window_start_date: date | None = None
    window_end_date: date | None = None

    def __post_init__(self) -> None:
        if self.match_ids is None:
            self.match_ids = set()

    def add(self, match_id: int, match_date: date | None, metric_value: float) -> None:
        self.metric_sum += metric_value
        self.metric_count += 1
        self.match_ids.add(match_id)
        if match_date is not None:
            if self.window_start_date is None or match_date < self.window_start_date:
                self.window_start_date = match_date
            if self.window_end_date is None or match_date > self.window_end_date:
                self.window_end_date = match_date

    def to_metric(self) -> TeamWindowMetric:
        metric_value = 0.0 if self.metric_count == 0 else round(self.metric_sum / self.metric_count, 4)
        return TeamWindowMetric(
            team_id=self.team_id,
            competition_id=self.competition_id,
            season_id=self.season_id,
            window_type=self.window_type,
            window_key=self.window_key,
            metric_key=self.metric_key,
            metric_value=metric_value,
            match_count=len(self.match_ids),
            window_start_date=self.window_start_date,
            window_end_date=self.window_end_date,
            metric_context={
                "aggregation": "mean",
                "input_metric_key": self.metric_key,
                "source_table": "team_match_metrics",
                "window_type": self.window_type,
            },
        )


def aggregate_team_window_metrics(rows: list[dict[str, Any]]) -> list[TeamWindowMetric]:
    buckets: dict[tuple[int, int | None, int | None, str, str, str], _WindowBucket] = {}

    for row in rows:
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
            team_id=team_id,
            competition_id=competition_id,
            season_id=season_id,
        ):
            bucket_key = (
                team_id,
                scoped_competition_id,
                scoped_season_id,
                window_type,
                window_key,
                metric_key,
            )
            bucket = buckets.get(bucket_key)
            if bucket is None:
                bucket = _WindowBucket(
                    team_id=team_id,
                    competition_id=scoped_competition_id,
                    season_id=scoped_season_id,
                    window_type=window_type,
                    window_key=window_key,
                    metric_key=metric_key,
                )
                buckets[bucket_key] = bucket
            bucket.add(match_id=match_id, match_date=match_date, metric_value=metric_value)

    metrics = [bucket.to_metric() for bucket in buckets.values()]
    return sorted(
        metrics,
        key=lambda item: (
            item.team_id,
            item.window_type,
            item.window_key,
            item.metric_key,
        ),
    )


def build_windows(
    team_id: int,
    competition_id: int | None,
    season_id: int | None,
) -> list[tuple[str, str, int | None, int | None]]:
    windows = [
        ("all_matches", f"team:{team_id}:all_matches", None, None),
    ]

    if competition_id is not None:
        windows.append(
            (
                "competition",
                f"team:{team_id}:competition:{competition_id}",
                competition_id,
                None,
            )
        )

    if season_id is not None:
        windows.append(
            (
                "season",
                f"team:{team_id}:season:{season_id}",
                None,
                season_id,
            )
        )

    if competition_id is not None and season_id is not None:
        windows.append(
            (
                "competition_season",
                f"team:{team_id}:competition:{competition_id}:season:{season_id}",
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
