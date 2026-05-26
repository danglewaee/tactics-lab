from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db import Database
from metrics.player_match import compute_player_match_metrics


@dataclass(slots=True)
class PlayerMatchMetricsRunSummary:
    matches_processed: int = 0
    player_rows_processed: int = 0
    player_metric_rows_written: int = 0


def compute_player_metrics_for_all_matches(database_url: str, limit_matches: int | None = None) -> PlayerMatchMetricsRunSummary:
    summary = PlayerMatchMetricsRunSummary()

    with Database(database_url) as database:
        matches = _load_matches(database, limit_matches=limit_matches)
        for match in matches:
            summary.matches_processed += 1
            match_id = int(match["match_id"])
            events = _load_match_events(database, match_id)
            lineups = _load_match_lineups(database, match_id)
            match_end_minute = _match_end_minute(events)

            for lineup_row in lineups:
                metrics = compute_player_match_metrics(events, lineup_row, match_end_minute)
                summary.player_rows_processed += 1
                summary.player_metric_rows_written += _upsert_player_metrics(
                    database,
                    match_id=match_id,
                    team_id=int(lineup_row["team_id"]),
                    player_id=int(lineup_row["player_id"]),
                    metrics=metrics,
                )

    return summary


def _load_matches(database: Database, limit_matches: int | None) -> list[dict[str, Any]]:
    sql = """
        select m.match_id
        from matches m
        where exists (select 1 from events e where e.match_id = m.match_id)
          and exists (select 1 from lineups l where l.match_id = m.match_id)
        order by m.match_date desc, m.match_id desc
    """
    params: tuple[Any, ...] = ()
    if limit_matches is not None:
        sql += " limit %s"
        params = (limit_matches,)

    with database.connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())


def _load_match_events(database: Database, match_id: int) -> list[dict[str, Any]]:
    with database.connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                match_id,
                index_in_match,
                minute,
                team_id,
                player_id,
                possession_id,
                play_pattern,
                event_type,
                outcome,
                x_start,
                y_start,
                x_end,
                y_end,
                pass_recipient_player_id
            from events
            where match_id = %s
            order by index_in_match
            """,
            (match_id,),
        )
        return list(cursor.fetchall())


def _load_match_lineups(database: Database, match_id: int) -> list[dict[str, Any]]:
    with database.connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select
                match_id,
                team_id,
                player_id,
                start_minute,
                end_minute,
                position_name,
                position_group
            from lineups
            where match_id = %s
            order by team_id, start_minute, player_id
            """,
            (match_id,),
        )
        return list(cursor.fetchall())


def _match_end_minute(events: list[dict[str, Any]]) -> int:
    max_minute = 0
    for event in events:
        minute = event.get("minute")
        if isinstance(minute, int) and minute > max_minute:
            max_minute = minute
    return max(max_minute, 90)


def _upsert_player_metrics(
    database: Database,
    match_id: int,
    team_id: int,
    player_id: int,
    metrics: dict[str, float],
) -> int:
    written = 0
    for key, value in metrics.items():
        database.execute(
            """
            insert into player_match_metrics (match_id, team_id, player_id, metric_key, metric_value, metric_context)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (match_id, player_id, metric_key) do update set
                team_id = excluded.team_id,
                metric_value = excluded.metric_value,
                metric_context = excluded.metric_context,
                computed_at = now()
            """,
            (
                match_id,
                team_id,
                player_id,
                key,
                value,
                database.jsonb({"source": "jobs.etl.metrics.player_pipeline"}),
            ),
        )
        written += 1
    return written


def dict_row(cursor: Any) -> Any:
    columns = [column.name for column in cursor.description]

    def factory(row: tuple[Any, ...]) -> dict[str, Any]:
        return dict(zip(columns, row))

    return factory
