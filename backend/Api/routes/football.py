from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from Api.services.football_analysis import (
    FootballAnalyzeRequest,
    FootballAnalyzeResponse,
    MatchPrepRequest,
    MatchPrepReport,
    OpponentScoutRequest,
    OpponentScoutReport,
    generate_match_prep_report,
    generate_opponent_scout,
    generate_opponent_report,
    list_serie_a_teams,
    list_teams,
)
from Api.services.football_pdf import build_match_prep_pdf, build_scout_pdf

log = logging.getLogger("vigia.football")
router = APIRouter(prefix="/api/football", tags=["football"])


# ---------------------------------------------------------------------------
# Match Prep
# ---------------------------------------------------------------------------

@router.post("/match-prep", response_model=MatchPrepReport)
def match_prep(payload: MatchPrepRequest):
    try:
        return generate_match_prep_report(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        log.error("match-prep failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Match prep failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Opponent Scout
# ---------------------------------------------------------------------------

@router.post("/opponent-scout", response_model=OpponentScoutReport)
def opponent_scout(payload: OpponentScoutRequest):
    try:
        return generate_opponent_scout(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        log.error("opponent-scout failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Scout failed: {exc}") from exc


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

class PdfExportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(match_prep|scout)$")
    language: str = Field(default="en", pattern="^(en|pt)$")
    report: dict


@router.post("/export-pdf")
def export_pdf(payload: PdfExportRequest):
    try:
        if payload.report_type == "match_prep":
            pdf_bytes = build_match_prep_pdf(payload.report, lang=payload.language)
            my_team = payload.report.get("my_team", "report")
            opp_team = payload.report.get("opponent_team", "")
            filename = f"match_prep_{my_team}_vs_{opp_team}.pdf".replace(" ", "_")
        else:
            pdf_bytes = build_scout_pdf(payload.report, lang=payload.language)
            team = payload.report.get("team", "scout")
            filename = f"scout_{team}.pdf".replace(" ", "_")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        log.error("export-pdf failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Team lists
# ---------------------------------------------------------------------------

@router.get("/serie-a/teams", response_model=list[str])
def serie_a_teams():
    try:
        teams = list_serie_a_teams()
        if not teams:
            raise HTTPException(status_code=503, detail="Could not fetch Série A standings from ESPN")
        return teams
    except HTTPException:
        raise
    except Exception as exc:
        log.error("serie-a/teams failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/teams")
def competition_teams(competition: str = "serie_a"):
    """Returns team list for the given competition. Includes group info for World Cup."""
    if competition not in ("serie_a", "world_cup"):
        raise HTTPException(status_code=400, detail="competition must be serie_a or world_cup")
    try:
        return list_teams(competition)
    except Exception as exc:
        log.error("teams failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Legacy
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
