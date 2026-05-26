from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db import Database
from metrics.player_window import PlayerWindowMetric, aggregate_player_window_metrics


@dataclass(slots=True)
class PlayerWindowMetricsRunSummary:
    rows_read: int = 0
    players_processed: int = 0
    windows_written: int = 0
    window_metric_rows_written: int = 0


def compute_player_window_metrics(
    database_url: str,
    player_id: int | None = None,
    team_id: int | None = None,
) -> PlayerWindowMetricsRunSummary:
    summary = PlayerWindowMetricsRunSummary()

    with Database(database_url) as database:
        rows = _load_player_match_metric_rows(database, player_id=player_id, team_id=team_id)
        summary.rows_read = len(rows)

        window_metrics = aggregate_player_window_metrics(rows)
        summary.players_processed = len({metric.player_id for metric in window_metrics})
        summary.windows_written = len(
            {(metric.player_id, metric.team_id, metric.window_type, metric.window_key) for metric in window_metrics}
        )

        for metric in window_metrics:
            _upsert_player_window_metric(database, metric)
            summary.window_metric_rows_written += 1

    return summary


def _load_player_match_metric_rows(
    database: Database,
    player_id: int | None,
    team_id: int | None,
) -> list[dict[str, Any]]:
    sql = """
        select
            pm.player_id,
            pm.team_id,
            pm.match_id,
            m.competition_id,
            m.season_id,
            m.match_date,
            pm.metric_key,
            pm.metric_value
        from player_match_metrics pm
        join matches m on m.match_id = pm.match_id
        where 1 = 1
    """
    params: list[Any] = []
    if player_id is not None:
        sql += " and pm.player_id = %s"
        params.append(player_id)
    if team_id is not None:
        sql += " and pm.team_id = %s"
        params.append(team_id)
    sql += " order by pm.player_id, pm.team_id, m.match_date, pm.match_id, pm.metric_key"

    with database.connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, tuple(params))
        return list(cursor.fetchall())


def _upsert_player_window_metric(database: Database, metric: PlayerWindowMetric) -> None:
    database.execute(
        """
        insert into player_window_metrics (
            player_id,
            team_id,
            competition_id,
            season_id,
            window_type,
            window_key,
            metric_key,
            metric_value,
            match_count,
            minutes_played_total,
            window_start_date,
            window_end_date,
            metric_context
        )
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        on conflict (player_id, team_id, window_type, window_key, metric_key) do update set
            competition_id = excluded.competition_id,
            season_id = excluded.season_id,
            metric_value = excluded.metric_value,
            match_count = excluded.match_count,
            minutes_played_total = excluded.minutes_played_total,
            window_start_date = excluded.window_start_date,
            window_end_date = excluded.window_end_date,
            metric_context = excluded.metric_context,
            computed_at = now()
        """,
        (
            metric.player_id,
            metric.team_id,
            metric.competition_id,
            metric.season_id,
            metric.window_type,
            metric.window_key,
            metric.metric_key,
            metric.metric_value,
            metric.match_count,
            metric.minutes_played_total,
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
