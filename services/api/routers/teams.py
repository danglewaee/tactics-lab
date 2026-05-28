from fastapi import APIRouter, HTTPException

from schemas.player import TeamPlayersResponse
from schemas.team import MatchWindowResponse, TeamDetail, TeamStyleResponse, TeamSummary
from services.editorial import get_team, get_team_players, get_team_style, list_team_matches, list_teams


router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamSummary])
def get_teams() -> list[TeamSummary]:
    return list_teams()


@router.get("/{team_slug}", response_model=TeamDetail)
def get_team_detail(team_slug: str) -> TeamDetail:
    team = get_team(team_slug)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return team


@router.get("/{team_slug}/matches", response_model=MatchWindowResponse)
def get_team_matches(team_slug: str) -> MatchWindowResponse:
    match_window = list_team_matches(team_slug)
    if match_window is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return match_window


@router.get("/{team_slug}/style", response_model=TeamStyleResponse)
def get_team_style_profile(team_slug: str) -> TeamStyleResponse:
    team_style = get_team_style(team_slug)
    if team_style is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return team_style


@router.get("/{team_slug}/players", response_model=TeamPlayersResponse)
def get_team_players_list(
    team_slug: str,
    competition_id: int | None = None,
    season_id: int | None = None,
    qualified_only: bool = True,
) -> TeamPlayersResponse:
    players = get_team_players(
        team_slug,
        competition_id=competition_id,
        season_id=season_id,
        qualified_only=qualified_only,
    )
    if players is None:
        raise HTTPException(status_code=404, detail="Team not found.")
    return players
