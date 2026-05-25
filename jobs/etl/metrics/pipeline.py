from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from db import Database
from metrics.team_match import compute_team_match_metrics
from reports.generator import build_team_match_takeaways


@dataclass(slots=True)
class MetricsRunSummary:
    matches_processed: int = 0
    team_metric_rows_written: int = 0
    reports_written: int = 0


def compute_metrics_for_all_matches(database_url: str, limit_matches: int | None = None) -> MetricsRunSummary:
    summary = MetricsRunSummary()

    with Database(database_url) as database:
        matches = _load_matches(database, limit_matches=limit_matches)
        for match in matches:
            summary.matches_processed += 1
            events = _load_match_events(database, int(match["match_id"]))
            teams = [
                (int(match["home_team_id"]), match["home_team_name"]),
                (int(match["away_team_id"]), match["away_team_name"]),
            ]

            for team_id, team_name in teams:
                metrics = compute_team_match_metrics(events, team_id)
                summary.team_metric_rows_written += _upsert_team_metrics(database, int(match["match_id"]), team_id, metrics)
                summary.reports_written += _upsert_tactical_report(
                    database,
                    match_id=int(match["match_id"]),
                    team_id=team_id,
                    team_name=str(team_name),
                    metrics=metrics,
                )

    return summary


def _load_matches(database: Database, limit_matches: int | None) -> list[dict[str, Any]]:
    sql = """
        select
            m.match_id,
            m.home_team_id,
            m.away_team_id,
            home.name as home_team_name,
            away.name as away_team_name
        from matches m
        join teams home on home.team_id = m.home_team_id
        join teams away on away.team_id = m.away_team_id
        where exists (select 1 from events e where e.match_id = m.match_id)
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
                team_id,
                possession_id,
                play_pattern,
                event_type,
                event_subtype,
                outcome,
                x_start,
                y_start,
                x_end,
                y_end
            from events
            where match_id = %s
            order by index_in_match
            """,
            (match_id,),
        )
        return list(cursor.fetchall())


def _upsert_team_metrics(database: Database, match_id: int, team_id: int, metrics: dict[str, float]) -> int:
    written = 0
    for key, value in metrics.items():
        database.execute(
            """
            insert into team_match_metrics (match_id, team_id, metric_key, metric_value, metric_context)
            values (%s, %s, %s, %s, %s)
            on conflict (match_id, team_id, metric_key) do update set
                metric_value = excluded.metric_value,
                metric_context = excluded.metric_context,
                computed_at = now()
            """,
            (match_id, team_id, key, value, database.jsonb({"source": "jobs.etl.metrics.pipeline"})),
        )
        written += 1
    return written


def _upsert_tactical_report(
    database: Database,
    match_id: int,
    team_id: int,
    team_name: str,
    metrics: dict[str, float],
) -> int:
    takeaways = build_team_match_takeaways(team_name, metrics)
    evidence = {
        key: metrics[key]
        for key in (
            "progressive_passes",
            "field_tilt",
            "left_lane_build_up_share",
            "center_lane_build_up_share",
            "right_lane_build_up_share",
            "high_regains",
        )
        if key in metrics
    }

    database.execute(
        """
        delete from tactical_reports
        where scope_type = 'match' and match_id = %s and subject_team_id = %s and report_version = 'v1'
        """,
        (match_id, team_id),
    )

    written = 0
    for index, takeaway in enumerate(takeaways, start=1):
        database.execute(
            """
            insert into tactical_reports (
                scope_type, scope_key, subject_team_id, match_id, title, summary, evidence, report_version
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "match",
                f"match:{match_id}:team:{team_id}:takeaway:{index}",
                team_id,
                match_id,
                f"Tactical takeaway {index}",
                takeaway,
                database.jsonb(evidence),
                "v1",
            ),
        )
        written += 1
    return written


def dict_row(cursor: Any) -> Any:
    columns = [column.name for column in cursor.description]

    def factory(row: tuple[Any, ...]) -> dict[str, Any]:
        return dict(zip(columns, row))

    return factory
