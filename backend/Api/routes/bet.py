"""Football Bet API — value board endpoint.

GET /api/bet/scan -> cached value board across active competitions (World Cup
for now). Cached ~30 min so visits don't burn Odds API credits.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from Api.services.bet_engine import build_board
from Api.services.bet_odds import OddsAPIError

log = logging.getLogger("vigia.bet")
router = APIRouter(prefix="/api/bet", tags=["bet"])


@router.get("/scan")
def scan_board(hours: int = 48, last_n: int = 8, min_edge: float = 0.02,
               max_events: int = 10):
    hours = max(1, min(hours, 168))
    last_n = max(1, min(last_n, 15))
    max_events = max(1, min(max_events, 20))
    try:
        return build_board(hours, last_n, min_edge, max_events)
    except OddsAPIError as exc:
        # Most likely ODDS_API_KEY missing in the server environment.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log.error("bet scan failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bet scan failed: {exc}") from exc
