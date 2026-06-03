from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from Api.services.football_analysis import (
    FootballAnalyzeRequest,
    FootballAnalyzeResponse,
    generate_opponent_report,
)


log = logging.getLogger("vigia.football")
router = APIRouter(prefix="/api/football", tags=["football"])


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
