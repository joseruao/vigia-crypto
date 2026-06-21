from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from Api.services.football_analysis import (
    FootballAnalyzeRequest,
    FootballAnalyzeResponse,
    FootballTeamContext,
    MatchPrepRequest,
    MatchPrepReport,
    generate_match_prep_report,
    generate_opponent_report,
    list_serie_a_teams,
)

log = logging.getLogger("vigia.football")
router = APIRouter(prefix="/api/football", tags=["football"])


@router.post("/match-prep", response_model=MatchPrepReport)
def match_prep(payload: MatchPrepRequest):
    """
    Generate a full match preparation report for an upcoming Série A game.

    Example:
        POST /api/football/match-prep
        { "my_team": "Cruzeiro", "opponent_team": "Flamengo" }
    """
    try:
        return generate_match_prep_report(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        log.error("match-prep failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Match prep failed: {exc}") from exc


@router.get("/serie-a/teams", response_model=list[str])
def serie_a_teams():
    """Return current Série A teams from FBref live standings."""
    try:
        teams = list_serie_a_teams()
        if not teams:
            raise HTTPException(status_code=503, detail="Could not fetch Série A standings from FBref")
        return teams
    except HTTPException:
        raise
    except Exception as exc:
        log.error("serie-a/teams failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Legacy endpoints kept for backward compatibility
# ---------------------------------------------------------------------------

@router.post("/analyze", response_model=FootballAnalyzeResponse)
def analyze_football_opponent(payload: FootballAnalyzeRequest):
    try:
        return generate_opponent_report(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        log.error("Football analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Football analysis failed") from exc
