from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db import Database
from metrics.team_window import TeamWindowMetric, aggregate_team_window_metrics


@dataclass(slots=True)
class TeamWindowMetricsRunSummary:
    rows_read: int = 0
    teams_processed: int = 0
    windows_written: int = 0
    window_metric_rows_written: int = 0


def compute_team_window_metrics(database_url: str, team_id: int | None = None) -> TeamWindowMetricsRunSummary:
    summary = TeamWindowMetricsRunSummary()

    with Database(database_url) as database:
        rows = _load_team_match_metric_rows(database, team_id=team_id)
        summary.rows_read = len(rows)

        window_metrics = aggregate_team_window_metrics(rows)
        summary.teams_processed = len({metric.team_id for metric in window_metrics})
        summary.windows_written = len({(metric.team_id, metric.window_type, metric.window_key) for metric in window_metrics})

        for metric in window_metrics:
            _upsert_team_window_metric(database, metric)
            summary.window_metric_rows_written += 1

    return summary


def _load_team_match_metric_rows(database: Database, team_id: int | None) -> list[dict[str, Any]]:
    sql = """
        select
            tm.team_id,
            tm.match_id,
            m.competition_id,
            m.season_id,
            m.match_date,
            tm.metric_key,
            tm.metric_value
        from team_match_metrics tm
        join matches m on m.match_id = tm.match_id
    """
    params: tuple[Any, ...] = ()
    if team_id is not None:
        sql += " where tm.team_id = %s"
        params = (team_id,)
    sql += " order by tm.team_id, m.match_date, tm.match_id, tm.metric_key"

    with database.connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())


def _upsert_team_window_metric(database: Database, metric: TeamWindowMetric) -> None:
    database.execute(
        """
        insert into team_window_metrics (
            team_id,
            competition_id,
            season_id,
            window_type,
            window_key,
            metric_key,
            metric_value,
            match_count,
            window_start_date,
            window_end_date,
            metric_context
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (team_id, window_type, window_key, metric_key) do update set
            competition_id = excluded.competition_id,
            season_id = excluded.season_id,
            metric_value = excluded.metric_value,
            match_count = excluded.match_count,
            window_start_date = excluded.window_start_date,
            window_end_date = excluded.window_end_date,
            metric_context = excluded.metric_context,
            computed_at = now()
        """,
        (
            metric.team_id,
            metric.competition_id,
            metric.season_id,
            metric.window_type,
            metric.window_key,
            metric.metric_key,
            metric.metric_value,
            metric.match_count,
            metric.window_start_date,
            metric.window_end_date,
            database.jsonb(metric.metric_context),
        ),
    )


def dict_row(cursor: Any) -> Any:
    columns = [column.name for column in cursor.description]

    def factory(row: tuple[Any, ...]) -> dict[str, Any]:
        return dict(zip(columns, row))

    return factory
