from typing import Literal

from pydantic import BaseModel, Field

from schemas.match import MatchCard


class TeamSummary(BaseModel):
    team_slug: str
    name: str
    short_name: str | None = None
    team_type: Literal["club", "national_team"]
    editorial_focus: bool = True


class TeamDetail(TeamSummary):
    thesis: str
    focus_areas: list[str] = Field(default_factory=list)
    target_metrics: list[str] = Field(default_factory=list)
    data_status: Literal["pending_ingestion", "partial", "ready"] = "pending_ingestion"


class MatchWindowResponse(BaseModel):
    team_slug: str
    team_name: str
    matches: list[MatchCard] = Field(default_factory=list)

