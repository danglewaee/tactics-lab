from typing import Literal

from pydantic import BaseModel, Field

from schemas.match import MetricValue


class TeamPlayersWindow(BaseModel):
    window_type: Literal["all_matches", "competition", "season", "competition_season"]
    label: str
    competition_id: int | None = None
    season_id: int | None = None
    match_count: int
    date_range_label: str | None = None
    qualification_minutes: int


class PlayerRoleCard(BaseModel):
    player_id: int
    name: str
    display_name: str | None = None
    primary_position: str | None = None
    position_group: str | None = None
    minutes_played_total: int
    match_count: int
    qualified: bool
    metrics: list[MetricValue] = Field(default_factory=list)


class TeamPlayersResponse(BaseModel):
    team_slug: str
    team_name: str
    data_status: Literal["pending_ingestion", "partial", "ready"] = "pending_ingestion"
    window: TeamPlayersWindow | None = None
    players: list[PlayerRoleCard] = Field(default_factory=list)
