from fastapi import APIRouter, HTTPException

from schemas.team import MatchWindowResponse, TeamDetail, TeamStyleResponse, TeamSummary
from services.editorial import get_team, get_team_style, list_team_matches, list_teams


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
