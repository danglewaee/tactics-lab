from __future__ import annotations

import re
from typing import Any

from schemas.match import MatchCard, MatchDetail, MatchNetwork, MatchReportBundle, MetricValue, TacticalTakeaway
from schemas.team import MatchWindowResponse, TeamDetail, TeamStyleResponse, TeamStyleWindow, TeamSummary
from services.database import DatabaseUnavailableError, query_all, query_one


DEFAULT_FOCUS_AREAS = ["build-up structure", "pressing behavior", "territorial control"]
DEFAULT_TARGET_METRICS = [
    "field_tilt",
    "progressive_passes",
    "left_lane_build_up_share",
    "center_lane_build_up_share",
    "right_lane_build_up_share",
    "high_regains",
]
DEFAULT_CHART_BLOCKS = [
    "pass_network",
    "build_up_lane_split",
    "regain_zone_map",
    "progressive_pass_map",
]
METRIC_LABELS = {
    "progressive_passes": "Progressive passes",
    "field_tilt": "Field tilt",
    "left_lane_build_up_share": "Left build-up share",
    "center_lane_build_up_share": "Center build-up share",
    "right_lane_build_up_share": "Right build-up share",
    "high_regains": "High regains",
}


EDITORIAL_TEAMS: dict[str, TeamDetail] = {
    "manchester-united": TeamDetail(
        team_slug="manchester-united",
        name="Manchester United",
        short_name="MU",
        team_type="club",
        thesis="Track how Manchester United builds through the first and second phases and where the press wins the ball back.",
        focus_areas=["build-up shape", "progressive passing", "pressing regain zones"],
        target_metrics=[
            "field_tilt",
            "left_lane_build_up_share",
            "center_lane_build_up_share",
            "right_lane_build_up_share",
            "high_regains",
        ],
        data_status="partial",
    ),
    "portugal": TeamDetail(
        team_slug="portugal",
        name="Portugal",
        short_name="POR",
        team_type="national_team",
        thesis="Explain how Portugal balances central progression, wide overloads, and counterpress behavior across tournament matches.",
        focus_areas=["rest defense", "build-up direction", "counterpress regains"],
        target_metrics=[
            "field_tilt",
            "verticality_index",
            "counterpress_regains",
            "progressive_passes",
        ],
        data_status="partial",
    ),
}

MATCH_WINDOWS: dict[str, MatchWindowResponse] = {
    "manchester-united": MatchWindowResponse(
        team_slug="manchester-united",
        team_name="Manchester United",
        matches=[
            MatchCard(
                match_id="mu-bootstrap-001",
                title="Manchester United build-up bootstrap report",
                subject_team_slug="manchester-united",
                subject_team_name="Manchester United",
                focus_areas=["first phase structure", "pressing regain height"],
            )
        ],
    ),
    "portugal": MatchWindowResponse(
        team_slug="portugal",
        team_name="Portugal",
        matches=[
            MatchCard(
                match_id="por-bootstrap-001",
                title="Portugal tactical bootstrap report",
                subject_team_slug="portugal",
                subject_team_name="Portugal",
                focus_areas=["left-lane progression", "counterpress regains"],
            )
        ],
    ),
}

MATCH_DETAILS: dict[str, MatchDetail] = {
    "mu-bootstrap-001": MatchDetail(
        match_id="mu-bootstrap-001",
        title="Manchester United build-up bootstrap report",
        subject_team_slug="manchester-united",
        subject_team_name="Manchester United",
        chart_blocks=DEFAULT_CHART_BLOCKS,
        focus_areas=["first phase structure", "pressing regain height"],
        takeaways=[
            TacticalTakeaway(
                title="Editorial placeholder",
                detail="This report is waiting for event data ingestion. The endpoint shape is ready for real tactical output.",
                evidence_keys=["data_status"],
            )
        ],
    ),
    "por-bootstrap-001": MatchDetail(
        match_id="por-bootstrap-001",
        title="Portugal tactical bootstrap report",
        subject_team_slug="portugal",
        subject_team_name="Portugal",
        chart_blocks=["field_tilt", "build_up_lane_split", "counterpress_regains"],
        focus_areas=["left-lane progression", "counterpress regains"],
        takeaways=[
            TacticalTakeaway(
                title="Editorial placeholder",
                detail="The product language for Portugal is wired in before real match data lands in the database.",
                evidence_keys=["editorial_focus"],
            )
        ],
    ),
}


def list_teams() -> list[TeamSummary]:
    rows = _query_rows_safe(
        """
        select
            t.team_id,
            t.external_id,
            t.name,
            t.short_name,
            t.country_name,
            t.team_type,
            count(distinct m.match_id) as match_count
        from teams t
        left join matches m on m.home_team_id = t.team_id or m.away_team_id = t.team_id
        group by t.team_id, t.external_id, t.name, t.short_name, t.country_name, t.team_type
        order by lower(t.name)
        """
    )
    if rows:
        return [_team_summary_from_row(row) for row in rows]
    return [TeamSummary(**team.model_dump()) for team in EDITORIAL_TEAMS.values()]


def get_team(team_slug: str) -> TeamDetail | None:
    row = _load_team_row_by_slug(team_slug)
    if row is not None:
        return _team_detail_from_row(row)
    return EDITORIAL_TEAMS.get(team_slug)


def list_team_matches(team_slug: str) -> MatchWindowResponse | None:
    row = _load_team_row_by_slug(team_slug)
    if row is None:
        return MATCH_WINDOWS.get(team_slug)

    matches = _query_rows_safe(
        """
        select
            m.match_id,
            m.external_id,
            m.match_date,
            m.kickoff_at,
            m.home_score,
            m.away_score,
            home.team_id as home_team_id,
            home.name as home_team_name,
            away.team_id as away_team_id,
            away.name as away_team_name,
            exists(select 1 from events e where e.match_id = m.match_id) as has_events
        from matches m
        join teams home on home.team_id = m.home_team_id
        join teams away on away.team_id = m.away_team_id
        where m.home_team_id = %s or m.away_team_id = %s
        order by m.match_date desc, m.kickoff_at desc nulls last, m.match_id desc
        limit 20
        """,
        (row["team_id"], row["team_id"]),
    )

    return MatchWindowResponse(
        team_slug=team_slug,
        team_name=row["name"],
        matches=[_match_card_from_row(match_row, team_slug, row["name"]) for match_row in matches],
    )


def get_team_style(team_slug: str) -> TeamStyleResponse | None:
    row = _load_team_row_by_slug(team_slug)
    if row is None:
        editorial = EDITORIAL_TEAMS.get(team_slug)
        if editorial is None:
            return None
        return TeamStyleResponse(
            team_slug=team_slug,
            team_name=editorial.name,
            data_status="partial",
            windows=[],
        )

    team_id = int(row["team_id"])
    windows = _load_team_style_windows(team_id)
    if windows:
        return TeamStyleResponse(
            team_slug=team_slug,
            team_name=row["name"],
            data_status="ready",
            windows=windows,
        )

    return TeamStyleResponse(
        team_slug=team_slug,
        team_name=row["name"],
        data_status="partial" if _team_has_events(team_id) else "pending_ingestion",
        windows=[],
    )


def get_match_detail(match_id: str) -> MatchDetail | None:
    row = _load_match_row(match_id)
    if row is None:
        return MATCH_DETAILS.get(match_id)

    subject_slug, subject_name = _subject_team_for_match(row)
    focus_areas = _focus_areas_for_slug(subject_slug)
    subject_team_id = _subject_team_id_for_match(row, subject_slug)
    metrics = _load_match_metrics(int(row["match_id"]), subject_team_id)
    reports = _load_match_takeaways(int(row["match_id"]), subject_team_id=subject_team_id)

    if not reports:
        reports = [
            TacticalTakeaway(
                title="Metrics pending",
                detail=(
                    "Match and event data are loaded from the database. Tactical reports will appear after metric and report jobs run."
                    if row["has_events"]
                    else "Match metadata exists in the database, but event data has not been ingested yet."
                ),
                evidence_keys=["events", "tactical_reports"],
            )
        ]

    return MatchDetail(
        match_id=str(row["match_id"]),
        title=_match_title(row),
        subject_team_slug=subject_slug,
        subject_team_name=subject_name,
        data_status="ready" if row["has_events"] else "pending_ingestion",
        chart_blocks=DEFAULT_CHART_BLOCKS if row["has_events"] else [],
        focus_areas=focus_areas,
        metrics=metrics,
        takeaways=reports,
    )


def get_match_network(match_id: str) -> MatchNetwork | None:
    row = _load_match_row(match_id)
    if row is None:
        if match_id not in MATCH_DETAILS:
            return None
        return MatchNetwork(match_id=match_id)

    return MatchNetwork(
        match_id=str(row["match_id"]),
        data_status="ready" if row["has_events"] else "pending_ingestion",
    )


def get_match_reports(match_id: str) -> MatchReportBundle | None:
    row = _load_match_row(match_id)
    if row is None:
        match = MATCH_DETAILS.get(match_id)
        if match is None:
            return None
        return MatchReportBundle(match_id=match_id, generated=True, reports=match.takeaways)

    reports = _load_match_takeaways(row["match_id"])
    return MatchReportBundle(
        match_id=str(row["match_id"]),
        generated=bool(reports),
        reports=reports,
    )


def _team_summary_from_row(row: dict[str, Any]) -> TeamSummary:
    team_slug = _slugify(row["name"])
    editorial = EDITORIAL_TEAMS.get(team_slug)
    return TeamSummary(
        team_slug=team_slug,
        name=row["name"],
        short_name=row.get("short_name"),
        team_type=_resolve_team_type(row, editorial),
        editorial_focus=team_slug in EDITORIAL_TEAMS,
    )


def _team_detail_from_row(row: dict[str, Any]) -> TeamDetail:
    team_slug = _slugify(row["name"])
    editorial = EDITORIAL_TEAMS.get(team_slug)
    has_events = _team_has_events(int(row["team_id"]))

    if editorial is not None:
        return TeamDetail(
            team_slug=team_slug,
            name=row["name"],
            short_name=row.get("short_name") or editorial.short_name,
            team_type=_resolve_team_type(row, editorial),
            editorial_focus=True,
            thesis=editorial.thesis,
            focus_areas=editorial.focus_areas,
            target_metrics=editorial.target_metrics,
            data_status="ready" if has_events else "partial",
        )

    return TeamDetail(
        team_slug=team_slug,
        name=row["name"],
        short_name=row.get("short_name"),
        team_type=_resolve_team_type(row, editorial),
        editorial_focus=False,
        thesis=f"Analyze {row['name']}'s build-up patterns, pressing behavior, and territorial control across ingested matches.",
        focus_areas=DEFAULT_FOCUS_AREAS,
        target_metrics=DEFAULT_TARGET_METRICS,
        data_status="ready" if has_events else "pending_ingestion",
    )


def _match_card_from_row(match_row: dict[str, Any], subject_team_slug: str, subject_team_name: str) -> MatchCard:
    return MatchCard(
        match_id=str(match_row["match_id"]),
        title=_match_title(match_row),
        subject_team_slug=subject_team_slug,
        subject_team_name=subject_team_name,
        data_status="ready" if match_row["has_events"] else "pending_ingestion",
        focus_areas=_focus_areas_for_slug(subject_team_slug),
    )


def _load_team_row_by_slug(team_slug: str) -> dict[str, Any] | None:
    for row in _query_rows_safe(
        """
        select
            t.team_id,
            t.external_id,
            t.name,
            t.short_name,
            t.country_name,
            t.team_type,
            count(distinct m.match_id) as match_count
        from teams t
        left join matches m on m.home_team_id = t.team_id or m.away_team_id = t.team_id
        group by t.team_id, t.external_id, t.name, t.short_name, t.country_name, t.team_type
        order by lower(t.name)
        """
    ):
        if _slugify(row["name"]) == team_slug:
            return row
    return None


def _team_has_events(team_id: int) -> bool:
    row = _query_row_safe(
        """
        select exists(
            select 1
            from events e
            join matches m on m.match_id = e.match_id
            where m.home_team_id = %s or m.away_team_id = %s
        ) as has_events
        """,
        (team_id, team_id),
    )
    return bool(row and row.get("has_events"))


def _load_match_row(match_id: str) -> dict[str, Any] | None:
    return _query_row_safe(
        """
        select
            m.match_id,
            m.external_id,
            m.match_date,
            m.kickoff_at,
            m.home_score,
            m.away_score,
            home.team_id as home_team_id,
            home.name as home_team_name,
            home.short_name as home_team_short_name,
            away.team_id as away_team_id,
            away.name as away_team_name,
            away.short_name as away_team_short_name,
            exists(select 1 from events e where e.match_id = m.match_id) as has_events
        from matches m
        join teams home on home.team_id = m.home_team_id
        join teams away on away.team_id = m.away_team_id
        where m.match_id::text = %s or m.external_id = %s
        order by m.match_id desc
        limit 1
        """,
        (match_id, match_id),
    )


def _load_match_takeaways(match_id: int, subject_team_id: int | None = None) -> list[TacticalTakeaway]:
    sql = """
        select title, summary, evidence
        from tactical_reports
        where match_id = %s
    """
    params: tuple[Any, ...] = (match_id,)
    if subject_team_id is not None:
        sql += " and subject_team_id = %s"
        params += (subject_team_id,)
    sql += " order by tactical_report_id asc limit 5"

    rows = _query_rows_safe(sql, params)
    takeaways: list[TacticalTakeaway] = []
    for row in rows:
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        takeaways.append(
            TacticalTakeaway(
                title=row["title"],
                detail=row["summary"],
                evidence_keys=sorted(evidence.keys()),
            )
        )
    return takeaways


def _load_match_metrics(match_id: int, team_id: int) -> list[MetricValue]:
    rows = _query_rows_safe(
        """
        select metric_key, metric_value
        from team_match_metrics
        where match_id = %s and team_id = %s
        order by metric_key
        """,
        (match_id, team_id),
    )
    return [_metric_value_from_row(row) for row in rows if row.get("metric_key") in METRIC_LABELS]


def _load_team_style_windows(team_id: int) -> list[TeamStyleWindow]:
    rows = _query_rows_safe(
        """
        select
            tw.window_type,
            tw.window_key,
            tw.match_count,
            tw.window_start_date,
            tw.window_end_date,
            tw.metric_key,
            tw.metric_value,
            c.name as competition_name,
            s.name as season_name
        from team_window_metrics tw
        left join competitions c on c.competition_id = tw.competition_id
        left join seasons s on s.season_id = tw.season_id
        where tw.team_id = %s
        order by
            case tw.window_type
                when 'all_matches' then 1
                when 'competition_season' then 2
                when 'competition' then 3
                when 'season' then 4
                else 5
            end,
            tw.window_end_date desc nulls last,
            tw.window_key,
            tw.metric_key
        """,
        (team_id,),
    )

    windows: list[TeamStyleWindow] = []
    by_window_key: dict[tuple[str, str], TeamStyleWindow] = {}

    for row in rows:
        metric_key = row.get("metric_key")
        if metric_key not in METRIC_LABELS:
            continue

        window_index = (str(row["window_type"]), str(row["window_key"]))
        window = by_window_key.get(window_index)
        if window is None:
            window = TeamStyleWindow(
                window_type=row["window_type"],
                window_key=row["window_key"],
                label=_team_style_window_label(row),
                match_count=int(row["match_count"]),
                date_range_label=_date_range_label(row.get("window_start_date"), row.get("window_end_date")),
                metrics=[],
            )
            by_window_key[window_index] = window
            windows.append(window)

        window.metrics.append(_metric_value_from_row(row))

    return windows


def _subject_team_for_match(match_row: dict[str, Any]) -> tuple[str, str]:
    home_slug = _slugify(match_row["home_team_name"])
    away_slug = _slugify(match_row["away_team_name"])
    if home_slug in EDITORIAL_TEAMS and away_slug not in EDITORIAL_TEAMS:
        return home_slug, match_row["home_team_name"]
    if away_slug in EDITORIAL_TEAMS and home_slug not in EDITORIAL_TEAMS:
        return away_slug, match_row["away_team_name"]
    return home_slug, match_row["home_team_name"]


def _subject_team_id_for_match(match_row: dict[str, Any], subject_slug: str) -> int:
    if _slugify(match_row["home_team_name"]) == subject_slug:
        return int(match_row["home_team_id"])
    return int(match_row["away_team_id"])


def _match_title(match_row: dict[str, Any]) -> str:
    home = match_row["home_team_name"]
    away = match_row["away_team_name"]
    if match_row.get("home_score") is None or match_row.get("away_score") is None:
        return f"{home} vs {away}"
    return f"{home} {match_row['home_score']}-{match_row['away_score']} {away}"


def _focus_areas_for_slug(team_slug: str) -> list[str]:
    editorial = EDITORIAL_TEAMS.get(team_slug)
    return editorial.focus_areas if editorial is not None else DEFAULT_FOCUS_AREAS


def _resolve_team_type(row: dict[str, Any], editorial: TeamDetail | None) -> str:
    if editorial is not None:
        return editorial.team_type
    if row.get("team_type") in {"club", "national_team"}:
        return row["team_type"]
    if row.get("country_name") and str(row["country_name"]).strip().lower() == str(row["name"]).strip().lower():
        return "national_team"
    return "club"


def _metric_value_from_row(row: dict[str, Any]) -> MetricValue:
    key = str(row["metric_key"])
    value = float(row["metric_value"])
    return MetricValue(
        key=key,
        label=METRIC_LABELS.get(key, key.replace("_", " ").title()),
        value=value,
        display_value=_format_metric_value(key, value),
    )


def _format_metric_value(key: str, value: float) -> str:
    if key.endswith("_share") or key == "field_tilt":
        return f"{value * 100:.1f}%"
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"


def _team_style_window_label(row: dict[str, Any]) -> str:
    window_type = str(row["window_type"])
    competition_name = row.get("competition_name")
    season_name = row.get("season_name")

    if window_type == "all_matches":
        return "All ingested matches"
    if window_type == "competition_season":
        if competition_name and season_name:
            return f"{competition_name} · {season_name}"
        if competition_name:
            return str(competition_name)
        if season_name:
            return str(season_name)
        return "Competition + season"
    if window_type == "competition":
        return str(competition_name or "Competition window")
    if window_type == "season":
        return str(season_name or "Season window")
    return window_type.replace("_", " ").title()


def _date_range_label(start_date: Any, end_date: Any) -> str | None:
    if not start_date and not end_date:
        return None
    if start_date and end_date:
        return f"{start_date} to {end_date}"
    return str(start_date or end_date)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _query_rows_safe(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        return query_all(sql, params)
    except DatabaseUnavailableError:
        return []


def _query_row_safe(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    try:
        return query_one(sql, params)
    except DatabaseUnavailableError:
        return None
