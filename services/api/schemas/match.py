from typing import Literal

from pydantic import BaseModel, Field


class TacticalTakeaway(BaseModel):
    title: str
    detail: str
    evidence_keys: list[str] = Field(default_factory=list)


class MatchCard(BaseModel):
    match_id: str
    title: str
    subject_team_slug: str
    subject_team_name: str
    data_status: Literal["pending_ingestion", "ready"] = "pending_ingestion"
    focus_areas: list[str] = Field(default_factory=list)


class MatchDetail(MatchCard):
    chart_blocks: list[str] = Field(default_factory=list)
    takeaways: list[TacticalTakeaway] = Field(default_factory=list)


class NetworkNode(BaseModel):
    player_name: str
    x: float
    y: float
    touches: int


class NetworkEdge(BaseModel):
    source_player: str
    target_player: str
    pass_count: int


class MatchNetwork(BaseModel):
    match_id: str
    data_status: Literal["pending_ingestion", "ready"] = "pending_ingestion"
    nodes: list[NetworkNode] = Field(default_factory=list)
    edges: list[NetworkEdge] = Field(default_factory=list)


class MatchReportBundle(BaseModel):
    match_id: str
    generated: bool
    reports: list[TacticalTakeaway] = Field(default_factory=list)

