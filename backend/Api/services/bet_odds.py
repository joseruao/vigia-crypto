"""
The Odds API client — Football Bet project.

Thin wrapper over https://the-odds-api.com. Reads ODDS_API_KEY from the
environment (free tier = 500 credits/month). Kept deliberately small: one
session, explicit credit accounting, and only the endpoints we actually need.

Credit cost model (per The Odds API docs):
  - /sports                         -> 0 credits
  - /sports/{sport}/odds            -> 1 credit per market per region
  - /sports/{sport}/events          -> 0 credits
  - /sports/{sport}/events/{id}/odds-> 1 credit per market per region
    (additional markets — corners/cards — live ONLY on this per-event endpoint)

So probing corners+cards for one match (eu region) = 2 credits. Budgeting
matters on the free tier; every call returns the remaining quota from the
response headers so callers can stop before hitting zero.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests

BASE = "https://api.the-odds-api.com/v4"

# Soccer leagues with enough fixtures per season for averages to carry signal.
# (The killer caveat from project_football_bet: the World Cup's 3-games-per-team
#  is noise; these league sport_keys are where the tool lives.)
LEAGUE_KEYS = {
    "epl": "soccer_epl",
    "serie_a": "soccer_italy_serie_a",
    "la_liga": "soccer_spain_la_liga",
    "bundesliga": "soccer_germany_bundesliga",
    "ligue_one": "soccer_france_ligue_one",
    "brazil": "soccer_brazil_campeonato",
}

# Markets we care about. "Featured" markets are available on the bulk
# /odds endpoint; "additional" markets (corners/cards/player props) are only
# on the per-event endpoint and only from selected bookmakers.
FEATURED_MARKETS = ["h2h", "totals", "btts"]
ADDITIONAL_MARKETS = [
    "alternate_totals_corners",   # total corners O/U
    "corners_1x2",
    "alternate_totals_cards",     # total cards/bookings O/U
    "player_shots_on_target",
]


class OddsAPIError(RuntimeError):
    pass


@dataclass
class Quota:
    used: int | None = None
    remaining: int | None = None
    last_cost: int | None = None

    def update(self, headers) -> None:
        def _int(h):
            v = headers.get(h)
            try:
                return int(v)
            except (TypeError, ValueError):
                return None
        self.used = _int("x-requests-used")
        self.remaining = _int("x-requests-remaining")
        self.last_cost = _int("x-requests-last")


@dataclass
class OddsClient:
    api_key: str = field(default_factory=lambda: os.getenv("ODDS_API_KEY", ""))
    region: str = "eu"          # eu = European bookmakers (Bet365, Pinnacle, etc.)
    quota: Quota = field(default_factory=Quota)

    def __post_init__(self):
        if not self.api_key:
            raise OddsAPIError(
                "ODDS_API_KEY not set. Get a free key (500 credits/month) at "
                "https://the-odds-api.com and add ODDS_API_KEY=... to .env"
            )
        self._s = requests.Session()

    def _get(self, path: str, **params) -> list | dict:
        params["apiKey"] = self.api_key
        r = self._s.get(f"{BASE}{path}", params=params, timeout=20)
        self.quota.update(r.headers)
        if r.status_code == 401:
            raise OddsAPIError("401 — invalid API key")
        if r.status_code == 422:
            raise OddsAPIError(f"422 — bad params/market for this sport: {r.text[:300]}")
        if r.status_code == 429:
            raise OddsAPIError("429 — out of credits for this month")
        if r.status_code != 200:
            raise OddsAPIError(f"{r.status_code} — {r.text[:300]}")
        return r.json()

    # -- 0-credit calls -----------------------------------------------------
    def list_sports(self) -> list[dict]:
        return self._get("/sports")  # type: ignore[return-value]

    def list_events(self, sport_key: str) -> list[dict]:
        return self._get(f"/sports/{sport_key}/events")  # type: ignore[return-value]

    # -- billed calls -------------------------------------------------------
    def featured_odds(self, sport_key: str, markets=None) -> list[dict]:
        """Bulk odds for all upcoming events. 1 credit per market per region."""
        markets = markets or FEATURED_MARKETS
        return self._get(  # type: ignore[return-value]
            f"/sports/{sport_key}/odds",
            regions=self.region,
            markets=",".join(markets),
            oddsFormat="decimal",
        )

    def event_odds(self, sport_key: str, event_id: str, markets) -> dict:
        """Per-event odds — the ONLY place corners/cards live.
        1 credit per market per region."""
        return self._get(  # type: ignore[return-value]
            f"/sports/{sport_key}/events/{event_id}/odds",
            regions=self.region,
            markets=",".join(markets),
            oddsFormat="decimal",
        )
