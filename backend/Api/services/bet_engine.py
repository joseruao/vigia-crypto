"""
Value engine — Football Bet project.

Ties the two halves together for a competition's upcoming fixtures:

    The Odds API (real odds)  +  ESPN history (our rate estimate)  ->  edges

For each upcoming match it:
  1. pulls odds for the markets we model (goals/corners/cards O/U),
  2. resolves both teams to ESPN and reads their recent per-game counts,
  3. builds a Poisson match-total lambda (sum of the two teams' shrunk rates),
  4. compares our P(over/under) to each bookmaker's de-vigged price,
  5. surfaces only positive-edge bets, loudly flagging thin samples.

HONEST FRAMING (see project_football_bet): corners/cards on the free tier come
almost entirely from Pinnacle — the sharpest book in the market. De-vigged
Pinnacle is close to the true price, so genuine +EV there is rare and small;
treat those as "model-vs-sharp" signals, not edges to hammer. Goals totals have
broader (softer) book coverage, where line divergence is more exploitable. This
is an informational divergence finder, not a profit promise.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from Api.services.bet_odds import OddsClient, OddsAPIError
from Api.services.bet_model import match_total_lambda, value_edge_from_lambda, Edge

# Odds API sport_key  ->  ESPN _COMPS competition key
ESPN_COMP = {
    "soccer_fifa_world_cup": "world_cup",
    "soccer_italy_serie_a": "ita_serie_a",
    "soccer_epl": "epl",
    "soccer_spain_la_liga": "la_liga",
    "soccer_germany_bundesliga": "bundesliga",
    "soccer_france_ligue_one": "ligue_1",
}

# Which competitions the tool actually runs right now. The 5 big leagues are
# off-season until ~21 Aug 2026, so the only live football is the World Cup —
# small samples, acknowledged noise, but it's what's playing. Add the league
# sport_keys back here when they kick off in August. (Mirrors the Football Lab's
# ACTIVE_COMPETITIONS toggle.)
ACTIVE_BET_COMPETITIONS = [
    "soccer_fifa_world_cup",
]

# our_market -> (odds_api_market_key, model_market, espn_stat_extractor)
MARKET_SPEC = {
    "goals": ("totals", "goals"),
    "corners": ("alternate_totals_corners", "corners"),
    "cards": ("alternate_totals_cards", "cards"),
}

# The Odds API and ESPN spell some national teams differently — without this the
# team is "unresolved" and we get no history (and thus no model rate). Keys are
# Odds API names, values ESPN names. (World Cup 2026 set; extend as needed.)
ODDS_TO_ESPN_TEAM = {
    "Bosnia & Herzegovina": "Bosnia-Herzegovina",
    "Czech Republic": "Czechia",
    "DR Congo": "Congo DR",
    "Turkey": "Türkiye",
    "USA": "United States",
}


@dataclass
class TeamHistory:
    name: str                       # canonical ESPN name (or input if unresolved)
    resolved: bool
    goals_for: list[float] = field(default_factory=list)
    corners_for: list[float] = field(default_factory=list)
    cards_for: list[float] = field(default_factory=list)

    def series(self, market: str) -> list[float]:
        return {"goals": self.goals_for, "corners": self.corners_for,
                "cards": self.cards_for}.get(market, [])


def _num(v) -> float | None:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def team_history(comp_key: str, team_name: str, last_n: int = 8) -> TeamHistory:
    """Per-game goals/corners/cards the team itself produced, from ESPN."""
    from Api.services.football_providers import get_provider
    from Api.services.football_analysis import _teams_match

    prov = get_provider()
    team_name = ODDS_TO_ESPN_TEAM.get(team_name, team_name)
    canon = prov.resolve_team(team_name, comp_key) or team_name
    hist = TeamHistory(name=canon, resolved=canon != team_name or True)
    try:
        matches = prov.get_team_matches(canon, comp_key, last_n=last_n)
    except Exception:
        matches = []
    if not matches:
        hist.resolved = False
        return hist

    for m in matches:
        score = m.get("score")
        if score and _teams_match(canon, m.get("home", "")):
            gf = _num(score.split("-")[0])
        elif score and _teams_match(canon, m.get("away", "")):
            gf = _num(score.split("-")[1])
        else:
            gf = None
        if gf is not None:
            hist.goals_for.append(gf)

        stats = (m.get("detail") or {}).get("stats", {})
        tstats = None
        for tname, s in stats.items():
            if _teams_match(canon, tname):
                tstats = s
                break
        if tstats:
            c = _num(tstats.get("corners"))
            if c is not None:
                hist.corners_for.append(c)
            yc = _num(tstats.get("yellow_cards")) or 0.0
            rc = _num(tstats.get("red_cards")) or 0.0
            if tstats.get("yellow_cards") not in (None, ""):
                hist.cards_for.append(yc + rc)
    return hist


def _extract_lines(event_odds: dict, odds_api_market: str) -> dict:
    """{ book_title: { point: {"over": price, "under": price} } } for one market."""
    out: dict = {}
    for b in event_odds.get("bookmakers", []):
        title = b.get("title", b.get("key", "?"))
        for m in b.get("markets", []):
            if m.get("key") != odds_api_market:
                continue
            for o in m.get("outcomes", []):
                name = (o.get("name") or "").lower()
                pt = o.get("point")
                price = o.get("price")
                if pt is None or price is None or name not in ("over", "under"):
                    continue
                out.setdefault(title, {}).setdefault(float(pt), {})[name] = float(price)
    return out


@dataclass
class MatchValue:
    sport_key: str
    home: str
    away: str
    commence: str
    home_hist: TeamHistory
    away_hist: TeamHistory
    edges: list[dict] = field(default_factory=list)  # serialisable edge rows

    def to_dict(self) -> dict:
        picks = curate_edges(self.edges)
        return {
            "sport_key": self.sport_key,
            "home": self.home, "away": self.away,
            "commence": self.commence,
            "home_resolved": self.home_hist.resolved,
            "away_resolved": self.away_hist.resolved,
            "home_games": len(self.home_hist.goals_for),
            "away_games": len(self.away_hist.goals_for),
            "min_games": min(len(self.home_hist.goals_for), len(self.away_hist.goals_for)),
            "picks": picks,                 # one best pick per market (the curated view)
            "candidates": len(self.edges),  # how many raw value rows were collapsed
            "edges": self.edges,            # full list (CLI / debugging)
        }


def curate_edges(edges: list[dict]) -> list[dict]:
    """Collapse the raw value rows into one best pick per market.

    Two layers of de-duplication:
      1. The SAME bet (market, line, side) appears once per bookmaker — keep only
         the best price (highest odd → highest EV for our fixed model prob).
      2. A market offers many lines (corners over 7.5/8.5/9.5...) — keep only the
         single highest-EV line per market.
    Result: at most one pick per market (goals/corners/cards), sorted best-first.
    The top row is flagged `best=True`.
    """
    best_price: dict = {}
    for e in edges:
        k = (e["market"], e["line"], e["side"])
        if k not in best_price or e["odd"] > best_price[k]["odd"]:
            best_price[k] = e

    per_market: dict = {}
    for e in best_price.values():
        m = e["market"]
        if m not in per_market or e["ev_per_unit"] > per_market[m]["ev_per_unit"]:
            per_market[m] = e

    picks = sorted(per_market.values(), key=lambda e: e["ev_per_unit"], reverse=True)
    out = []
    for i, e in enumerate(picks):
        row = dict(e)
        row["best"] = (i == 0)
        out.append(row)
    return out


def scan_event(client: OddsClient, sport_key: str, event: dict,
               last_n: int = 8, min_edge: float = 0.02) -> MatchValue:
    comp_key = ESPN_COMP.get(sport_key)
    home, away = event.get("home_team", ""), event.get("away_team", "")
    hh = team_history(comp_key, home, last_n) if comp_key else TeamHistory(home, False)
    ah = team_history(comp_key, away, last_n) if comp_key else TeamHistory(away, False)
    mv = MatchValue(sport_key, home, away, event.get("commence_time", ""), hh, ah)

    for our_mkt, (api_mkt, model_mkt) in MARKET_SPEC.items():
        try:
            odds = client.event_odds(sport_key, event["id"], [api_mkt])
        except OddsAPIError:
            continue
        lam, eff = match_total_lambda(hh.series(model_mkt), ah.series(model_mkt), model_mkt)
        if eff == 0:
            continue  # no history either side — can't model
        lines = _extract_lines(odds, api_mkt)
        for book, points in lines.items():
            for point, sides in points.items():
                if "over" not in sides or "under" not in sides:
                    continue
                for e in value_edge_from_lambda(model_mkt, point,
                                                sides["over"], sides["under"], lam, eff):
                    if e.is_value and e.edge >= min_edge:
                        mv.edges.append(_edge_row(our_mkt, book, e))
    mv.edges.sort(key=lambda r: r["ev_per_unit"], reverse=True)
    return mv


def _edge_row(market: str, book: str, e: Edge) -> dict:
    return {
        "market": market, "book": book, "line": e.line, "side": e.side,
        "odd": round(e.odd, 3), "model_prob": round(e.model_prob, 4),
        "fair_prob": round(e.fair_prob, 4), "edge": round(e.edge, 4),
        "ev_per_unit": round(e.ev_per_unit, 4), "n_games": e.n_games,
        "lambda": round(e.lam, 2), "warning": e.sample_warning,
    }


def scan(client: OddsClient, sport_key: str, hours_ahead: int = 72,
         last_n: int = 8, min_edge: float = 0.02, max_events: int = 12) -> list[MatchValue]:
    """Scan a competition's upcoming fixtures within `hours_ahead` for value."""
    now = datetime.now(timezone.utc)
    events = client.list_events(sport_key)
    upcoming = []
    for e in events:
        ct = e.get("commence_time", "")
        try:
            dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        except ValueError:
            continue
        hrs = (dt - now).total_seconds() / 3600
        if 0 <= hrs <= hours_ahead:
            upcoming.append((hrs, e))
    upcoming.sort(key=lambda t: t[0])
    return [scan_event(client, sport_key, e, last_n, min_edge)
            for _, e in upcoming[:max_events]]


def scan_active(client: OddsClient, hours_ahead: int = 72, last_n: int = 8,
                min_edge: float = 0.02, max_events: int = 12) -> list[MatchValue]:
    """Scan every currently-active competition (today: World Cup only)."""
    out: list[MatchValue] = []
    for sport_key in ACTIVE_BET_COMPETITIONS:
        out.extend(scan(client, sport_key, hours_ahead, last_n, min_edge, max_events))
    return out


DISCLAIMER = (
    "Informational tool, not financial advice. We surface where our data-derived "
    "estimate disagrees with the bookmaker's price — not guaranteed winners. "
    "Corners/cards come mostly from Pinnacle (a sharp book), so genuine value "
    "there is rare. During the World Cup samples are tiny (1-3 games), so most "
    "rows are flagged as thin-sample noise. Bet responsibly."
)


def build_board(hours_ahead: int = 48, last_n: int = 8, min_edge: float = 0.02,
                max_events: int = 10) -> dict:
    """JSON-serialisable value board across active competitions, cached ~30 min
    (via the football module's cache) so each page view does not spend credits."""
    from Api.services.football_analysis import _cached
    key = f"bet_board_{hours_ahead}_{last_n}_{min_edge}_{max_events}"
    return _cached(key, lambda: _build_board_uncached(
        hours_ahead, last_n, min_edge, max_events))


def _build_board_uncached(hours_ahead, last_n, min_edge, max_events) -> dict:
    client = OddsClient()  # raises OddsAPIError if ODDS_API_KEY is unset
    results = scan_active(client, hours_ahead, last_n, min_edge, max_events)
    matches = [mv.to_dict() for mv in results]
    return {
        "source": "The Odds API (odds) + ESPN (history)",
        "competitions": ACTIVE_BET_COMPETITIONS,
        "hours_ahead": hours_ahead,
        "last_n": last_n,
        "credits_remaining": client.quota.remaining,
        "total_value_rows": sum(len(m["picks"]) for m in matches),
        "disclaimer": DISCLAIMER,
        "matches": matches,
    }
