from schemas.match import MatchCard, MatchDetail, MatchNetwork, MatchReportBundle, TacticalTakeaway
from schemas.team import MatchWindowResponse, TeamDetail, TeamSummary


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
        chart_blocks=[
            "pass_network",
            "build_up_lane_split",
            "regain_zone_map",
            "progressive_pass_map",
        ],
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
        chart_blocks=[
            "field_tilt",
            "build_up_lane_split",
            "counterpress_regains",
        ],
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
    return [TeamSummary(**team.model_dump()) for team in EDITORIAL_TEAMS.values()]


def get_team(team_slug: str) -> TeamDetail | None:
    return EDITORIAL_TEAMS.get(team_slug)


def list_team_matches(team_slug: str) -> MatchWindowResponse | None:
    return MATCH_WINDOWS.get(team_slug)


def get_match_detail(match_id: str) -> MatchDetail | None:
    return MATCH_DETAILS.get(match_id)


def get_match_network(match_id: str) -> MatchNetwork | None:
    if match_id not in MATCH_DETAILS:
        return None
    return MatchNetwork(match_id=match_id)


def get_match_reports(match_id: str) -> MatchReportBundle | None:
    match = MATCH_DETAILS.get(match_id)
    if match is None:
        return None
    return MatchReportBundle(match_id=match_id, generated=True, reports=match.takeaways)

