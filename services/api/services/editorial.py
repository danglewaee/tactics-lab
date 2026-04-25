from __future__ import annotations

import re
from typing import Any

from schemas.match import MatchCard, MatchDetail, MatchNetwork, MatchReportBundle, TacticalTakeaway
from schemas.team import MatchWindowResponse, TeamDetail, TeamSummary
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


def get_match_detail(match_id: str) -> MatchDetail | None:
    row = _load_match_row(match_id)
    if row is None:
        return MATCH_DETAILS.get(match_id)

    subject_slug, subject_name = _subject_team_for_match(row)
    focus_areas = _focus_areas_for_slug(subject_slug)
    reports = _load_match_takeaways(row["match_id"])

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


def _load_match_takeaways(match_id: int) -> list[TacticalTakeaway]:
    rows = _query_rows_safe(
        """
        select title, summary, evidence
        from tactical_reports
        where match_id = %s
        order by created_at desc, tactical_report_id desc
        limit 5
        """,
        (match_id,),
    )
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


def _subject_team_for_match(match_row: dict[str, Any]) -> tuple[str, str]:
    home_slug = _slugify(match_row["home_team_name"])
    away_slug = _slugify(match_row["away_team_name"])
    if home_slug in EDITORIAL_TEAMS and away_slug not in EDITORIAL_TEAMS:
        return home_slug, match_row["home_team_name"]
    if away_slug in EDITORIAL_TEAMS and home_slug not in EDITORIAL_TEAMS:
        return away_slug, match_row["away_team_name"]
    return home_slug, match_row["home_team_name"]


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
