from fastapi import APIRouter, HTTPException

from schemas.match import MatchDetail, MatchNetwork, MatchReportBundle
from services.editorial import get_match_detail, get_match_network, get_match_reports


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/{match_id}", response_model=MatchDetail)
def read_match(match_id: str) -> MatchDetail:
    match = get_match_detail(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found.")
    return match


@router.get("/{match_id}/network", response_model=MatchNetwork)
def read_match_network(match_id: str) -> MatchNetwork:
    network = get_match_network(match_id)
    if network is None:
        raise HTTPException(status_code=404, detail="Match not found.")
    return network


@router.get("/{match_id}/reports", response_model=MatchReportBundle)
def read_match_reports(match_id: str) -> MatchReportBundle:
    reports = get_match_reports(match_id)
    if reports is None:
        raise HTTPException(status_code=404, detail="Match not found.")
    return reports

