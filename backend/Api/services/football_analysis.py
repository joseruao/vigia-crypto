from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from typing import Optional

import requests
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class MatchPrepRequest(BaseModel):
    my_team: str = Field(..., min_length=1, max_length=120)
    opponent_team: str = Field(..., min_length=1, max_length=120)
    extra_notes: str = Field(default="", max_length=5000)
    language: str = Field(default="en", pattern="^(en|pt)$")
    competition: str = Field(default="serie_a", pattern="^(serie_a|world_cup)$")


class OpponentScoutRequest(BaseModel):
    team: str = Field(..., min_length=1, max_length=120)
    extra_notes: str = Field(default="", max_length=5000)
    language: str = Field(default="en", pattern="^(en|pt)$")
    competition: str = Field(default="serie_a", pattern="^(serie_a|world_cup)$")


class MatchPrepReport(BaseModel):
    my_team: str
    opponent_team: str
    data_source: str
    executive_summary: str
    opponent_strengths: list[str]
    opponent_weaknesses: list[str]
    key_threats: list[str]
    tactical_approach: str
    pressing_triggers: list[str]
    attacking_approach: list[str]
    set_piece_plan: list[str]
    risk_assessment: str
    raw_stats_used: str
    # Deep analytics (optional — older clients ignore)
    opponent_danger_players: list[dict] = Field(default_factory=list)
    opponent_alerts: list[str] = Field(default_factory=list)
    opponent_goals_log: list[str] = Field(default_factory=list)
    my_team_alerts: list[str] = Field(default_factory=list)
    matchup_insights: list[str] = Field(default_factory=list)
    substitution_notes: list[str] = Field(default_factory=list)
    opponent_lineup: list[str] = Field(default_factory=list)
    opponent_tactical_evolution: dict = Field(default_factory=dict)
    opponent_ranks: list[dict] = Field(default_factory=list)
    comparison: list[dict] = Field(default_factory=list)
    viz_payload: dict = Field(default_factory=dict)
    images: dict = Field(default_factory=dict)


class OpponentScoutReport(BaseModel):
    team: str
    data_source: str
    executive_summary: str
    playing_style: str
    strengths: list[str]
    weaknesses: list[str]
    key_patterns: list[str]
    how_to_beat_them: list[str]
    pressing_vulnerabilities: list[str]
    set_piece_tendencies: list[str]
    form_analysis: str
    raw_stats_used: str
    # Deep analytics (provider-derived) — optional so older clients still work
    top_danger_players: list[dict] = Field(default_factory=list)
    key_alerts: list[str] = Field(default_factory=list)
    how_they_score: list[str] = Field(default_factory=list)
    how_they_concede: list[str] = Field(default_factory=list)
    goals_log_for: list[str] = Field(default_factory=list)
    goals_log_against: list[str] = Field(default_factory=list)
    probable_lineup: list[str] = Field(default_factory=list)
    has_xg: bool = False
    tactical_evolution: dict = Field(default_factory=dict)
    competition_ranks: list[dict] = Field(default_factory=list)
    # Raw viz payload for PDF chart rendering (frontend ignores it)
    viz_payload: dict = Field(default_factory=dict)
    # Base64 chart images for inline web display
    images: dict = Field(default_factory=dict)


# Legacy models kept for backward compat
class FootballAnalyzeRequest(BaseModel):
    team_name: str = Field(..., min_length=1, max_length=120)
    stats: str = Field(default="", max_length=12000)
    observations: str = Field(default="", max_length=20000)


class FootballAnalysisReport(BaseModel):
    executive_summary: str
    tactical_strengths: list[str]
    tactical_weaknesses: list[str]
    key_players_to_watch: list[str]
    recommended_match_strategy: str
    pressing_recommendations: list[str]
    set_piece_considerations: list[str]
    risk_assessment: str


class FootballAnalyzeResponse(BaseModel):
    team_name: str
    report: FootballAnalysisReport


class FootballTeamContext(BaseModel):
    team_name: str
    source: str
    stats: str
    observations: str


# ---------------------------------------------------------------------------
# ESPN unofficial API — no key required
# ---------------------------------------------------------------------------

_ESPN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

_COMPS: dict[str, dict] = {
    "serie_a": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/bra.1/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard",
        "label": "Campeonato Brasileiro Serie A",
        "date_range": f"{time.strftime('%Y')}0101-{time.strftime('%Y')}1231",
        "grouped": False,  # league table, not groups
    },
    "world_cup": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard",
        "label": "FIFA World Cup 2026",
        "date_range": "20260601-20260801",
        "grouped": True,  # group stage structure
    },
    # --- Football Bet project: high-sample European leagues (ESPN slugs). ---
    # Additive only; the Football Lab request models still validate
    # ^(serie_a|world_cup)$, so these are reachable by the bet engine, not the Lab UI.
    "ita_serie_a": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/ita.1/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard",
        "label": "Serie A (Italy)",
        "date_range": f"{time.strftime('%Y')}0101-{time.strftime('%Y')}1231",
        "grouped": False,
    },
    "epl": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
        "label": "Premier League (England)",
        "date_range": f"{time.strftime('%Y')}0101-{time.strftime('%Y')}1231",
        "grouped": False,
    },
    "la_liga": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/esp.1/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard",
        "label": "La Liga (Spain)",
        "date_range": f"{time.strftime('%Y')}0101-{time.strftime('%Y')}1231",
        "grouped": False,
    },
    "bundesliga": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/ger.1/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/scoreboard",
        "label": "Bundesliga (Germany)",
        "date_range": f"{time.strftime('%Y')}0101-{time.strftime('%Y')}1231",
        "grouped": False,
    },
    "ligue_1": {
        "standings": "https://site.api.espn.com/apis/v2/sports/soccer/fra.1/standings",
        "scoreboard": "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/scoreboard",
        "label": "Ligue 1 (France)",
        "date_range": f"{time.strftime('%Y')}0101-{time.strftime('%Y')}1231",
        "grouped": False,
    },
}

_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = int(os.getenv("FOOTBALL_CACHE_TTL_SECONDS", "1800"))


def _cached(key: str, fn):
    now = time.time()
    if key in _CACHE:
        ts, val = _CACHE[key]
        if now - ts < _CACHE_TTL:
            return val
    val = fn()
    _CACHE[key] = (now, val)
    return val


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, headers=_ESPN_HEADERS, params=params or {}, timeout=20)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

_ALIASES: dict[str, list[str]] = {
    "atletico mineiro": ["atletico-mg", "atletico mg", "galo", "atl\xe9tico-mg", "atl\xe9tico mineiro", "atl. mineiro"],
    "athletico paranaense": ["atletico-pr", "athletico-pr", "furacao", "athletico pr", "cap", "atletico paranaense"],
    "sao paulo": ["s\xe3o paulo", "sao paulo fc", "spfc"],
    "internacional": ["inter", "sc internacional"],
    "gremio": ["gr\xeamio", "gremio fbpa", "imortal"],
    "fluminense": ["flu"],
    "flamengo": ["fla", "cr flamengo"],
    "botafogo": ["bota", "botafogo fr"],
    "vasco": ["vasco da gama", "cr vasco da gama"],
    "corinthians": ["timao", "sc corinthians"],
    "palmeiras": ["verdao", "se palmeiras"],
    "santos": ["santos fc"],
    "cruzeiro": ["raposa", "cruzeiro ec"],
    "bragantino": ["rb bragantino", "red bull bragantino", "red bull"],
    "bahia": ["ec bahia"],
    "fortaleza": ["fortaleza ec"],
    "ceara": ["vozao", "ceara sc"],
    "sport": ["sport recife"],
    "cuiaba": ["cuiab\xe1", "cuiaba ec"],
    "america mineiro": ["am\xe9rica mineiro", "america-mg", "america mg"],
    "goias": ["go\xedas", "goias ec"],
    "coritiba": ["coritiba fbc"],
    "juventude": ["juventude ec"],
    "mirassol": ["mirassol fc"],
    "vitoria": ["vit\xf3ria", "ec vitoria"],
}


def _norm(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower().strip())


def _teams_match(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if na == nb or na in nb or nb in na:
        return True
    for aliases in _ALIASES.values():
        normed = [_norm(x) for x in aliases]
        if na in normed and nb in normed:
            return True
    return False


# ---------------------------------------------------------------------------
# ESPN data fetchers
# ---------------------------------------------------------------------------

def _parse_entries(entries: list[dict], group: str = "") -> list[dict]:
    rows = []
    for entry in entries:
        team = entry.get("team", {})
        stats_map = {s["name"]: s["value"] for s in entry.get("stats", []) if "value" in s}
        rows.append({
            "team": team.get("displayName", ""),
            "abbr": team.get("abbreviation", ""),
            "group": group,
            "rank": int(stats_map.get("rank", 0)),
            "mp": int(stats_map.get("gamesPlayed", 0)),
            "w": int(stats_map.get("wins", 0)),
            "d": int(stats_map.get("ties", 0)),
            "l": int(stats_map.get("losses", 0)),
            "gf": int(stats_map.get("pointsFor", 0)),
            "ga": int(stats_map.get("pointsAgainst", 0)),
            "gd": int(stats_map.get("pointDifferential", 0)),
            "pts": int(stats_map.get("points", 0)),
        })
    return rows


def _fetch_standings_raw(competition: str = "serie_a") -> list[dict]:
    cfg = _COMPS[competition]
    data = _get(cfg["standings"])
    rows: list[dict] = []
    if cfg["grouped"]:
        # World Cup: children = groups
        for group in data.get("children", []):
            gname = group.get("name", "")
            entries = group.get("standings", {}).get("entries", [])
            rows.extend(_parse_entries(entries, group=gname))
    else:
        entries = (
            data.get("children", [data])[0]
            .get("standings", data.get("standings", {}))
            .get("entries", [])
        )
        rows = _parse_entries(entries)
    return sorted(rows, key=lambda r: (r.get("group", ""), r["rank"]))


def _league_slug(competition: str) -> str:
    return _COMPS[competition]["standings"].split("/soccer/")[1].split("/")[0]


def _fetch_matches_raw(competition: str = "serie_a") -> list[dict]:
    cfg = _COMPS[competition]
    data = _get(cfg["scoreboard"], params={"dates": cfg["date_range"], "limit": 400})
    matches = []
    for ev in data.get("events", []):
        status = ev.get("status", {}).get("type", {}).get("name", "")
        comp = ev.get("competitions", [{}])[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        score = None
        if status == "STATUS_FULL_TIME":
            score = f"{home.get('score', '?')}-{away.get('score', '?')}"
        matches.append({
            "event_id": str(ev.get("id", "")),
            "_competition": competition,
            "date": ev.get("date", "")[:10],
            "home": home.get("team", {}).get("displayName", ""),
            "away": away.get("team", {}).get("displayName", ""),
            "score": score,
            "status": status,
            "round": comp.get("series", {}).get("title") or ev.get("season", {}).get("displayName", ""),
            "venue": ev.get("venue", {}).get("fullName", ""),
        })
    return matches


def _fetch_event_summary(event_id: str, competition: str) -> dict:
    """Fetch rich per-match data: scorers, possession, shots, cards, corners."""
    slug = _league_slug(competition)
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/summary"
    try:
        return _get(url, params={"event": event_id})
    except Exception:
        return {}


def _parse_match_detail(summary: dict) -> dict:
    """Extract scorers and per-team stats from ESPN summary response."""
    detail: dict = {"scorers": [], "stats": {}}

    # Goal scorers from keyEvents (ESPN soccer uses keyEvents, not scoringPlays)
    for ev in summary.get("keyEvents", []):
        if not ev.get("scoringPlay"):
            continue
        ptype = ev.get("type", {}).get("type", "")
        team = ev.get("team", {}).get("displayName", "")
        clock = ev.get("clock", {}).get("displayValue", "?")
        period = ev.get("period", {}).get("number", 1)
        # Rich text already formatted by ESPN e.g. "Julián Quiñones Goal"
        short = ev.get("shortText", "")
        full_text = ev.get("text", "")
        # Extract scorer from participants if available
        participants = ev.get("participants", [])
        scorer = participants[0].get("athlete", {}).get("displayName", "") if participants else ""
        if not scorer:
            scorer = short.replace(" Goal", "").replace(" goal", "").strip()
        own_goal = "own" in ptype.lower() or "owngoal" in ptype.lower()
        label = f"{scorer} ({team}) {clock}'"
        if period > 2:
            label += " [ET]"
        if own_goal:
            label += " [OG]"
        detail["scorers"].append(label)
        # Store full description for LLM context
        if full_text:
            detail.setdefault("goal_descriptions", []).append(full_text)

    # Box score stats per team (ESPN field names confirmed from API)
    for team_data in summary.get("boxscore", {}).get("teams", []):
        tname = team_data.get("team", {}).get("displayName", "")
        rs = {s["name"]: s.get("displayValue", str(s.get("value", "")))
              for s in team_data.get("statistics", [])}
        detail["stats"][tname] = {
            "possession": rs.get("possessionPct", ""),
            "shots": rs.get("totalShots", ""),
            "shots_on_target": rs.get("shotsOnTarget", ""),
            "corners": rs.get("wonCorners", ""),
            "fouls": rs.get("foulsCommitted", ""),
            "yellow_cards": rs.get("yellowCards", ""),
            "red_cards": rs.get("redCards", ""),
            "offsides": rs.get("offsides", ""),
            "pass_pct": rs.get("passPct", ""),
            "accurate_passes": rs.get("accuratePasses", ""),
            "total_passes": rs.get("totalPasses", ""),
            "tackles": rs.get("effectiveTackles", ""),
            "interceptions": rs.get("interceptions", ""),
            "long_ball_pct": rs.get("longballPct", ""),
        }
    return detail


def _enrich_matches(matches: list[dict], competition: str, limit: int = 80) -> list[dict]:
    """Add scorers + stats to the most recent finished matches."""
    finished = [m for m in matches if m.get("score")][-limit:]
    ids_to_fetch = {m["event_id"] for m in finished if m.get("event_id")}
    summaries: dict[str, dict] = {}
    for eid in ids_to_fetch:
        cache_key = f"summary_{eid}"
        summaries[eid] = _cached(cache_key, lambda eid=eid: _parse_match_detail(
            _fetch_event_summary(eid, competition)
        ))
    enriched = []
    for m in matches:
        if m.get("event_id") in summaries:
            m = {**m, "detail": summaries[m["event_id"]]}
        enriched.append(m)
    return enriched


def fetch_standings(competition: str = "serie_a") -> list[dict]:
    return _cached(f"standings_{competition}", lambda: _fetch_standings_raw(competition))


def fetch_schedule(competition: str = "serie_a") -> list[dict]:
    return _cached(f"schedule_{competition}", lambda: _fetch_matches_raw(competition))


def fetch_rich_schedule(competition: str = "serie_a") -> list[dict]:
    """Schedule enriched with per-match scorers and stats (cached separately)."""
    base = fetch_schedule(competition)
    return _cached(f"rich_schedule_{competition}",
                   lambda: _enrich_matches(base, competition))


def compute_team_analytics(team: str, competition: str, recent: list[dict],
                           lang: str = "en", render_images: bool = True) -> dict:
    """Shot-level analytics for a single team, reusable by Scout and Match Prep.
    Returns a dict with danger players, alerts, circumstances, insights text,
    viz payload, formation and (optionally) base64 chart images. Never raises."""
    from Api.services.football_providers import get_provider
    from Api.services import football_insights as fi

    provider = get_provider()
    deep = recent[-5:]
    out: dict = {
        "danger": [], "alerts": [], "circ_for": {}, "circ_against": {},
        "tend_for": {}, "tend_against": {}, "how_score": [], "how_concede": [],
        "insights_text": "", "viz_payload": {}, "lineup": [], "formation": {},
        "images": {}, "has_xg": False, "tactical_evolution": {},
    }
    try:
        shots = provider.get_shot_events(deep, team)
        goals = provider.get_goal_events(deep, team)
        danger = fi.player_danger_scores(shots, goals, top=3)
        circ_for = fi.goal_circumstances(goals, is_for=True)
        circ_against = fi.goal_circumstances(goals, is_for=False)
        set_pieces = fi.set_piece_breakdown(goals)
        tend_for = fi.shot_tendencies(shots, is_for=True)
        tend_against = fi.shot_tendencies(shots, is_for=False)
        alerts = fi.key_alerts(shots, goals, danger, circ_for, tend_against, lang=lang)
        lineup = provider.get_lineups(deep, team)
        formation = provider.get_formation(deep, team) if hasattr(provider, "get_formation") else {}
        per_match_formation = (provider.get_formation_per_match(deep, team)
                               if hasattr(provider, "get_formation_per_match") else [])
        tact_evo = fi.tactical_evolution(per_match_formation)
        insights_text = fi.insights_to_text(
            danger, circ_for, circ_against, set_pieces, tend_for, tend_against, provider.has_xg)
        viz_payload = {
            "shots": shots,
            "goal_minutes_for": fi.goal_minutes(goals, is_for=True),
            "goal_minutes_against": fi.goal_minutes(goals, is_for=False),
            "has_xg": provider.has_xg, "provider": provider.name,
            "lineup": [n for n, _ in lineup], "formation": formation,
        }
        images = {}
        if render_images:
            try:
                from Api.services import football_viz as fv
                images = fv.render_scout_images(viz_payload, team)
            except Exception:
                images = {}
        out.update({
            "danger": danger, "alerts": alerts, "circ_for": circ_for,
            "circ_against": circ_against, "tend_for": tend_for, "tend_against": tend_against,
            "how_score": fi.fmt_circumstance(circ_for, lang=lang, matches_analysed=len(deep)),
            "how_concede": fi.fmt_circumstance(circ_against, lang=lang, matches_analysed=len(deep)),
            "goals_log_for": fi.goal_log(goals, is_for=True),
            "goals_log_against": fi.goal_log(goals, is_for=False),
            "insights_text": insights_text, "viz_payload": viz_payload,
            "lineup": [n for n, _ in lineup], "formation": formation,
            "images": images, "has_xg": provider.has_xg,
            "tactical_evolution": tact_evo,
        })
    except Exception as exc:
        out["insights_text"] = f"(Shot-level analytics unavailable: {exc})"
    return out


def _ordinal(n: int, lang: str = "en") -> str:
    if lang == "pt":
        return f"{n}º"
    if 10 <= (n % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def team_rankings(team: str, standings: list[dict], lang: str = "en") -> list[dict]:
    """Rank a team against every team in the competition, per game (fair when
    match counts differ). Returns a list of
    {metric, label, value, rank, total, good, bad, text}. Empty if not enough
    teams or the team is not found. Pure data — the single biggest credibility
    win: turns a loose number into 'worst defence in the competition'."""
    rows = [r for r in standings if r.get("mp", 0) >= 1]
    if len(rows) < 4:
        return []
    me = next((r for r in rows if _teams_match(team, r["team"])), None)
    if not me:
        return []
    pt = lang == "pt"
    total = len(rows)

    def pg(r: dict, key: str) -> float:
        return r.get(key, 0) / max(r.get("mp", 0), 1)

    # (metric, stat key, higher_is_better, phrase)
    specs = [
        ("attack",  "gf",  True,  "melhor ataque" if pt else "best attack"),
        ("defence", "ga",  False, "melhor defesa" if pt else "best defence"),
        ("points",  "pts", True,  "em pontos/jogo" if pt else "on points/game"),
    ]
    labels = {
        "attack":  "Ataque" if pt else "Attack",
        "defence": "Defesa" if pt else "Defence",
        "points":  "Pontos/jogo" if pt else "Points/game",
    }
    out: list[dict] = []
    for metric, key, higher, phrase in specs:
        myval = pg(me, key)
        if higher:
            rank = 1 + sum(1 for r in rows if pg(r, key) > myval)
        else:
            rank = 1 + sum(1 for r in rows if pg(r, key) < myval)
        good = rank <= total / 3
        bad = rank > 2 * total / 3
        of = "de" if pt else "of"
        out.append({
            "metric": metric,
            "label": labels[metric],
            "value": f"{round(myval, 2):g}",
            "rank": rank,
            "total": total,
            "good": good,
            "bad": bad,
            "text": f"{_ordinal(rank, lang)} {phrase} ({of} {total})",
        })
    return out


def _rankings_text(ranks: list[dict], team: str, lang: str = "en") -> str:
    """Compact block for the LLM prompt so the narrative can cite standing."""
    if not ranks:
        return ""
    pt = lang == "pt"
    head = (f"RANKINGS NA COMPETIÇÃO ({team}, vs todas as {ranks[0]['total']} equipas):"
            if pt else
            f"COMPETITION RANKINGS ({team}, vs all {ranks[0]['total']} teams):")
    lines = [head]
    for r in ranks:
        flag = ("  <- ponto fraco" if pt else "  <- weakness") if r["bad"] else (
               ("  <- ponto forte" if pt else "  <- strength") if r["good"] else "")
        lines.append(f"  - {r['label']}: {r['value']}/game — {r['text']}{flag}")
    return "\n".join(lines)


def team_comparison(my_name: str, opp_name: str, my_row: dict | None, opp_row: dict | None,
                    my_an: dict, opp_an: dict, my_matches: list[dict], opp_matches: list[dict],
                    lang: str = "en") -> list[dict]:
    """Per-game, side-by-side metrics for a head-to-head comparison chart.
    Normalised per game so teams with different match counts compare fairly.
    Returns a list of {label, my, opp, my_disp, opp_disp}. Empty if no standings."""
    if not my_row or not opp_row:
        return []
    pt = lang == "pt"
    L = {
        "pts": "Pontos / jogo" if pt else "Points / game",
        "gf": "Golos marcados / jogo" if pt else "Goals scored / game",
        "ga": "Golos sofridos / jogo" if pt else "Goals conceded / game",
        "shots": "Remates / jogo" if pt else "Shots / game",
        "sot": "Remates ao alvo / jogo" if pt else "Shots on target / game",
    }

    def per_game(row: dict, key: str) -> float:
        mp = max(row.get("mp", 0), 1)
        return round(row.get(key, 0) / mp, 2)

    metrics: list[dict] = []
    for key, mkey in (("pts", "pts"), ("gf", "gf"), ("ga", "ga")):
        mv, ov = per_game(my_row, mkey), per_game(opp_row, mkey)
        metrics.append({"label": L[key], "my": mv, "opp": ov,
                        "my_disp": f"{mv:g}", "opp_disp": f"{ov:g}"})

    # Shot volume from last-5 analytics (graceful: only added if present)
    def shots_pg(an: dict, n: int) -> float:
        total = an.get("tend_for", {}).get("total", 0)
        return round(total / max(n, 1), 1)

    my_n, opp_n = len(my_matches[-5:]), len(opp_matches[-5:])
    my_sh, opp_sh = shots_pg(my_an, my_n), shots_pg(opp_an, opp_n)
    if my_sh or opp_sh:
        metrics.append({"label": L["shots"], "my": my_sh, "opp": opp_sh,
                        "my_disp": f"{my_sh:g}", "opp_disp": f"{opp_sh:g}"})

    return metrics


def matchup_layer(my: dict, opp: dict, lang: str = "en") -> list[str]:
    """Cross their attacking tendencies with our defensive weaknesses (and vice
    versa) to surface concrete matchup edges. Pure data, no LLM."""
    pt = lang == "pt"
    out: list[str] = []
    opp_att = opp.get("tend_for", {})
    my_def = my.get("tend_against", {})
    if opp_att.get("total", 0) >= 4 and my_def.get("total", 0) >= 4:
        for side, key in (("centro" if pt else "centre", "central_pct"),
                          ("esquerda" if pt else "left", "left_pct"),
                          ("direita" if pt else "right", "right_pct")):
            oa, md = opp_att.get(key, 0), my_def.get(key, 0)
            if oa >= 40 and md >= 40:
                out.append(
                    f"PERIGO: eles atacam {oa}% pelo {side} e nós concedemos {md}% pelo mesmo lado"
                    if pt else
                    f"DANGER: they attack {oa}% via the {side} and we concede {md}% there"
                )
    # Set-piece clash — require a real sample on both sides (>= 3 goals each)
    # so we never produce a misleading "100% vs 100%" off one goal apiece.
    opp_c = opp.get("circ_for", {})
    my_c = my.get("circ_against", {})
    if opp_c.get("total", 0) >= 3 and my_c.get("total", 0) >= 3:
        opp_sp, my_sp_conc = opp_c.get("set_piece_pct", 0), my_c.get("set_piece_pct", 0)
        if opp_sp >= 33 and my_sp_conc >= 33:
            out.append(
                f"PERIGO: {opp_sp}% dos golos deles vêm de bolas paradas e nós sofremos {my_sp_conc}% assim"
                if pt else
                f"DANGER: {opp_sp}% of their goals come from set pieces and we concede {my_sp_conc}% the same way"
            )
    return out


# Backwards compat aliases
def fetch_serie_a_standings() -> list[dict]:
    return fetch_standings("serie_a")

def fetch_serie_a_schedule() -> list[dict]:
    return fetch_schedule("serie_a")

def list_serie_a_teams() -> list[str]:
    return [r["team"] for r in fetch_standings("serie_a")]

def list_teams(competition: str = "serie_a") -> list[dict]:
    rows = fetch_standings(competition)
    if competition == "world_cup":
        # Return with group info
        return [{"team": r["team"], "group": r.get("group", "")} for r in rows]
    return [{"team": r["team"], "group": ""} for r in rows]


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def _find_team_row(team: str, standings: list[dict]) -> Optional[dict]:
    for row in standings:
        if _teams_match(team, row["team"]):
            return row
    return None


def _team_recent(team: str, schedule: list[dict], n: int = 6) -> list[dict]:
    finished = [
        m for m in schedule
        if m.get("score") and (_teams_match(team, m["home"]) or _teams_match(team, m["away"]))
    ]
    return finished[-n:]


def _head_to_head(a: str, b: str, schedule: list[dict]) -> list[dict]:
    return [
        m for m in schedule
        if (
            (_teams_match(a, m["home"]) and _teams_match(b, m["away"])) or
            (_teams_match(b, m["home"]) and _teams_match(a, m["away"]))
        )
    ]


def _fmt_standing(row: dict) -> str:
    mp = max(row["mp"], 1)
    ppg = round(row["pts"] / mp, 2)
    avg_gf = round(row["gf"] / mp, 2)
    avg_ga = round(row["ga"] / mp, 2)
    return (
        f"#{row['rank']} {row['team']} | {row['mp']}MP | "
        f"W{row['w']} D{row['d']} L{row['l']} | Pts {row['pts']} ({ppg}ppg) | "
        f"GF {row['gf']} ({avg_gf}/g) GA {row['ga']} ({avg_ga}/g) GD {row['gd']:+d}"
    )


def _fmt_match(m: dict, perspective: str, neutral_venue: bool = False) -> str:
    score = m.get("score") or "upcoming"
    result = ""
    if m.get("score"):
        h, a = m["score"].split("-")
        h, a = int(h), int(a)
        if _teams_match(perspective, m["home"]):
            result = "W" if h > a else ("D" if h == a else "L")
        else:
            result = "W" if a > h else ("D" if h == a else "L")

    if neutral_venue:
        side = ""
    else:
        side = " [H]" if _teams_match(perspective, m["home"]) else " [A]"

    line = f"{m['date']} | {m['home']} {score} {m['away']}{side} {result}"

    detail = m.get("detail", {})
    scorers = detail.get("scorers", [])
    stats = detail.get("stats", {})

    if scorers:
        line += f"\n      Goals: {', '.join(scorers)}"

    # Show stats for perspective team
    t_stats = None
    for tname, ts in stats.items():
        if _teams_match(perspective, tname):
            t_stats = ts
            break
    if t_stats:
        parts = []
        if t_stats.get("possession"):
            try: parts.append(f"Poss {float(t_stats['possession']):.1f}%")
            except: parts.append(f"Poss {t_stats['possession']}%")
        if t_stats.get("shots") and t_stats.get("shots_on_target"):
            parts.append(f"Shots {t_stats['shots_on_target']}/{t_stats['shots']} on tgt")
        if t_stats.get("corners"):
            parts.append(f"Corners {t_stats['corners']}")
        if t_stats.get("pass_pct") and t_stats.get("accurate_passes"):
            try: parts.append(f"Passes {t_stats['accurate_passes']}/{t_stats.get('total_passes','')} ({float(t_stats['pass_pct'])*100:.0f}%)")
            except: pass
        if t_stats.get("yellow_cards") and t_stats["yellow_cards"] != "0":
            parts.append(f"YC {t_stats['yellow_cards']}")
        if t_stats.get("red_cards") and t_stats["red_cards"] != "0":
            parts.append(f"RC {t_stats['red_cards']}")
        if parts:
            line += f"\n      Stats: {' | '.join(parts)}"

    return line


def _comp_context(competition: str) -> str:
    if competition == "world_cup":
        return (
            "COMPETITION CONTEXT: FIFA World Cup 2026, hosted at NEUTRAL VENUES in USA, Mexico, and Canada. "
            "There is NO home advantage — all matches are on neutral ground. "
            "NEVER mention 'home crowd support', 'home advantage', or 'home performance' as a strength. "
            "Do not label teams as 'home' or 'away' — use their actual names. "
            "Teams have played very few matches (group stage). Be careful not to over-extrapolate from limited data."
        )
    return (
        "COMPETITION CONTEXT: Campeonato Brasileiro Série A. "
        "Home/away splits are significant in Brazilian football — explicitly analyse them. "
        "Teams have played multiple matches — use patterns and trends in the data."
    )


def _form_string(team: str, recent: list[dict]) -> str:
    results = []
    for m in recent:
        if not m.get("score"):
            continue
        h, a = m["score"].split("-")
        h, a = int(h), int(a)
        if _teams_match(team, m["home"]):
            results.append("W" if h > a else ("D" if h == a else "L"))
        else:
            results.append("W" if a > h else ("D" if h == a else "L"))
    return "".join(results) or "no data"


# ---------------------------------------------------------------------------
# Match prep report
# ---------------------------------------------------------------------------

def generate_match_prep_report(req: MatchPrepRequest) -> MatchPrepReport:
    comp = getattr(req, "competition", "serie_a")
    neutral = comp == "world_cup"
    standings = fetch_standings(comp)
    schedule = fetch_rich_schedule(comp)

    my_row = _find_team_row(req.my_team, standings)
    opp_row = _find_team_row(req.opponent_team, standings)
    my_recent = _team_recent(req.my_team, schedule)
    opp_recent = _team_recent(req.opponent_team, schedule)
    h2h = _head_to_head(req.my_team, req.opponent_team, schedule)

    my_stats_str = _fmt_standing(my_row) if my_row else f"{req.my_team}: NOT FOUND in current standings"
    opp_stats_str = _fmt_standing(opp_row) if opp_row else f"{req.opponent_team}: NOT FOUND in current standings"
    my_form = _form_string(req.my_team, my_recent)
    opp_form = _form_string(req.opponent_team, opp_recent)

    my_recent_str = "\n".join(f"  {_fmt_match(m, req.my_team, neutral)}" for m in my_recent) or "  no data"
    opp_recent_str = "\n".join(f"  {_fmt_match(m, req.opponent_team, neutral)}" for m in opp_recent) or "  no data"
    h2h_played = [m for m in h2h if m.get("score")]
    h2h_str = (
        "\n".join(
            f"  {m['date']} | {m['home']} {m['score']} {m['away']}"
            for m in h2h_played
        )
        or "  no previous meetings this season"
    )

    # Competition rankings for both teams (per game, vs all teams)
    my_ranks = team_rankings(req.my_team, standings, lang=req.language)
    opp_ranks = team_rankings(req.opponent_team, standings, lang=req.language)
    my_ranks_block = _rankings_text(my_ranks, req.my_team, lang=req.language)
    opp_ranks_block = _rankings_text(opp_ranks, req.opponent_team, lang=req.language)

    comp_label = _COMPS[comp]["label"]
    raw_stats = "\n".join([
        f"MY TEAM [{my_form}]:  {my_stats_str}",
        f"OPPONENT [{opp_form}]: {opp_stats_str}",
        "",
        my_ranks_block,
        "",
        opp_ranks_block,
        "",
        f"MY TEAM — LAST {len(my_recent)} MATCHES (with match stats where available):",
        my_recent_str,
        "",
        f"OPPONENT — LAST {len(opp_recent)} MATCHES (with match stats where available):",
        opp_recent_str,
        "",
        "HEAD-TO-HEAD (this season):",
        h2h_str,
    ])

    # ---- Deep analytics for BOTH teams + matchup layer ----
    opp_an = compute_team_analytics(req.opponent_team, comp, opp_recent, lang=req.language, render_images=True)
    my_an = compute_team_analytics(req.my_team, comp, my_recent, lang=req.language, render_images=False)
    matchups = matchup_layer(my_an, opp_an, lang=req.language)

    analytics_block = "\n".join([
        "=== OPPONENT SHOT-LEVEL ANALYTICS ===",
        opp_an["insights_text"],
        "",
        "=== OUR TEAM SHOT-LEVEL ANALYTICS (self-scout) ===",
        my_an["insights_text"],
        "",
        "=== MATCHUP EDGES (their attack vs our defence) ===",
        ("\n".join(f"  - {m}" for m in matchups) if matchups else "  (no strong matchup pattern detected)"),
    ])
    raw_stats = raw_stats + "\n\n" + analytics_block

    extra = f"\n\nADDITIONAL COACH NOTES:\n{req.extra_notes}" if req.extra_notes.strip() else ""
    lang = getattr(req, "language", "en")
    lang_instruction = (
        "CRITICAL INSTRUCTION: You MUST write every single word of your response in Brazilian Portuguese. "
        "This includes ALL JSON string values — executive_summary, tactical_approach, every list item, everything. "
        "Do NOT write any English. Use football terminology standard in Brazil."
        if lang == "pt"
        else "Write the entire report in English."
    )

    prompt = f"""You are the lead analyst for a professional football club.
The head coach needs a match preparation report.

LANGUAGE: {lang_instruction}

{_comp_context(comp)}

MY TEAM: {req.my_team}
OPPONENT: {req.opponent_team}

=== DATA SOURCE: ESPN {comp_label} ===

{raw_stats}{extra}

VOICE & STYLE — write like an assistant coach, not an AI:
- Direct, concrete, imperative. Short sentences. BANNED: "exhibits", "showcases", "balanced", "demonstrates", "overall".
- Every claim cites evidence — a name, %, count or scoreline. No filler.

ANALYSIS INSTRUCTIONS:
- Work ONLY from the data above. Do not invent stats, players, or physical attributes (you do NOT know who is "faster" — never claim it).
- You have shot-level analytics for BOTH teams plus a MATCHUP EDGES block. Build the game plan around those edges.
- Name the opponent's dangerous players. Pin our attacking plan to THEIR defensive weakness (use their "how they concede" / shot sides).
- Pin our defensive plan to THEIR attack (their danger players, shot sides, set-piece %).
- For substitution_notes: ONLY pattern-based, data-grounded suggestions (e.g. "their #9 fades after 70' — our fresh CBs can step up late"; "we concede late — plan a defensive sub around 70'"). Do NOT invent player attributes. If no data supports a suggestion, return an empty list.

SMALL-SAMPLE RULE (critical for credibility):
- If a team has played fewer than 3 matches OR scored fewer than 3 goals, NEVER use percentages for goal types — use absolute counts and flag the limited sample.
- NEVER write "100%" off one or two goals.

Return EXACTLY this JSON (no extra keys, no markdown):
{{
  "executive_summary": "MILITARY LABEL STYLE: exactly 4-5 lines, each a LABEL in CAPS + colon + short value, separated by newline characters (\\n). Use these labels: POSSESSION ADVANTAGE, MAIN THREAT, OPPONENT WEAKNESS, KEY OPPORTUNITY (and optionally KEY RISK). Example: 'POSSESSION ADVANTAGE: Spain\\nMAIN THREAT: Maxi Araujo (Uruguay)\\nOPPONENT WEAKNESS: Central defence + set pieces\\nKEY OPPORTUNITY: Attack their right side'. Each value short and concrete. No prose sentences.",
  "opponent_strengths": ["data-backed strength with evidence 1", "strength 2", "strength 3"],
  "opponent_weaknesses": ["exploitable weakness with evidence 1", "weakness 2", "weakness 3"],
  "key_threats": ["named opponent player or pattern to neutralise, with evidence 1", "threat 2"],
  "tactical_approach": "CHECKLIST: 4-6 short imperative instructions, one per line, each starting with '✓ ', separated by newline characters (\\n). Example: '✓ Defend centrally\\n✓ Exploit their set pieces\\n✓ Mark Maxi Araujo aggressively\\n✓ Attack the right side\\n✓ Avoid open transitions'. Each line max 6 words. No prose.",
  "pressing_triggers": ["specific moment/situation to press 1", "trigger 2"],
  "attacking_approach": ["instruction tied to THEIR defensive weakness 1", "instruction 2", "instruction 3"],
  "set_piece_plan": ["set piece insight from the data 1", "consideration 2"],
  "risk_assessment": "main risks in this matchup and how to mitigate them",
  "substitution_notes": ["pattern-based substitution/rotation suggestion 1", "..."]
}}"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0.15,
    )

    raw = json.loads(resp.choices[0].message.content or "{}")

    def to_list(v: object) -> list[str]:
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    warnings = []
    if not my_row:
        warnings.append(f"WARNING: '{req.my_team}' not matched in standings")
    if not opp_row:
        warnings.append(f"WARNING: '{req.opponent_team}' not matched in standings")

    comp_label = _COMPS.get(comp, _COMPS["serie_a"])["label"]
    source = f"{comp_label} Dataset ({len(schedule)} fixtures, {len(standings)} teams)"
    if warnings:
        source += " | " + " | ".join(warnings)

    # Opponent dossier images + my-team shot maps for the matchup view
    images = dict(opp_an.get("images", {}))

    # Head-to-head comparison (data for web bars + rendered chart for PDF)
    comparison = team_comparison(
        req.my_team, req.opponent_team, my_row, opp_row,
        my_an, opp_an, my_recent, opp_recent, lang=req.language,
    )
    if comparison:
        try:
            from Api.services import football_viz as fv
            comp_title = ("Comparação directa (por jogo)" if req.language == "pt"
                          else "Head-to-Head (per game)")
            comp_uri = fv.render_comparison_image(
                req.my_team, req.opponent_team, comparison, comp_title)
            if comp_uri:
                images["comparison"] = comp_uri
        except Exception:
            pass

    # Prefix opponent images so they don't clash, keep simple keys the PDF/web expect
    return MatchPrepReport(
        my_team=req.my_team,
        opponent_team=req.opponent_team,
        data_source=source,
        executive_summary=str(raw.get("executive_summary", "")).strip(),
        opponent_strengths=to_list(raw.get("opponent_strengths")),
        opponent_weaknesses=to_list(raw.get("opponent_weaknesses")),
        key_threats=to_list(raw.get("key_threats")),
        tactical_approach=str(raw.get("tactical_approach", "")).strip(),
        pressing_triggers=to_list(raw.get("pressing_triggers")),
        attacking_approach=to_list(raw.get("attacking_approach")),
        set_piece_plan=to_list(raw.get("set_piece_plan")),
        risk_assessment=str(raw.get("risk_assessment", "")).strip(),
        raw_stats_used=raw_stats,
        opponent_danger_players=opp_an.get("danger", []),
        opponent_alerts=opp_an.get("alerts", []),
        opponent_goals_log=opp_an.get("goals_log_for", []),
        my_team_alerts=my_an.get("alerts", []),
        matchup_insights=matchups,
        substitution_notes=to_list(raw.get("substitution_notes")),
        opponent_lineup=opp_an.get("lineup", []),
        opponent_tactical_evolution=opp_an.get("tactical_evolution", {}),
        opponent_ranks=opp_ranks,
        comparison=comparison,
        viz_payload=opp_an.get("viz_payload", {}),
        images=images,
    )


# ---------------------------------------------------------------------------
# Opponent Scout — deep single-team analysis
# ---------------------------------------------------------------------------

def generate_opponent_scout(req: OpponentScoutRequest) -> OpponentScoutReport:
    comp = getattr(req, "competition", "serie_a")
    neutral = comp == "world_cup"
    standings = fetch_standings(comp)
    schedule = fetch_rich_schedule(comp)

    row = _find_team_row(req.team, standings)
    recent = _team_recent(req.team, schedule, n=10)

    stats_str = _fmt_standing(row) if row else f"{req.team}: NOT FOUND in current standings"
    form = _form_string(req.team, recent)

    def goals_for(matches, team):
        return [int(m["score"].split("-")[0 if _teams_match(team, m["home"]) else 1])
                for m in matches if m.get("score")]

    def goals_against(matches, team):
        return [int(m["score"].split("-")[1 if _teams_match(team, m["home"]) else 0])
                for m in matches if m.get("score")]

    def avg(lst): return round(sum(lst) / len(lst), 2) if lst else 0.0

    if neutral:
        location_breakdown = f"ALL MATCHES AT NEUTRAL VENUES ({len(recent)} games played)"
    else:
        home_m = [m for m in recent if _teams_match(req.team, m["home"])]
        away_m = [m for m in recent if not _teams_match(req.team, m["home"])]
        location_breakdown = (
            f"HOME ({len(home_m)} games): avg {avg(goals_for(home_m, req.team))} scored / "
            f"{avg(goals_against(home_m, req.team))} conceded | "
            f"AWAY ({len(away_m)} games): avg {avg(goals_for(away_m, req.team))} scored / "
            f"{avg(goals_against(away_m, req.team))} conceded"
        )

    # Aggregate match stats across all recent games
    total_shots, total_sot, total_corners, total_yc = [], [], [], []
    total_poss = []
    for m in recent:
        detail = m.get("detail", {})
        for tname, ts in detail.get("stats", {}).items():
            if not _teams_match(req.team, tname):
                continue
            if ts.get("shots"):
                try: total_shots.append(float(ts["shots"]))
                except: pass
            if ts.get("shots_on_target"):
                try: total_sot.append(float(ts["shots_on_target"]))
                except: pass
            if ts.get("corners"):
                try: total_corners.append(float(ts["corners"]))
                except: pass
            if ts.get("yellow_cards"):
                try: total_yc.append(float(ts["yellow_cards"]))
                except: pass
            if ts.get("possession"):
                try: total_poss.append(float(str(ts["possession"]).replace("%", "")))
                except: pass

    agg_stats_parts = []
    if total_shots:
        agg_stats_parts.append(f"avg shots/game: {avg(total_shots)} ({avg(total_sot)} on target)")
    if total_corners:
        agg_stats_parts.append(f"avg corners/game: {avg(total_corners)}")
    if total_poss:
        agg_stats_parts.append(f"avg possession: {avg(total_poss):.1f}%")
    if total_yc:
        agg_stats_parts.append(f"avg yellow cards/game: {avg(total_yc):.1f}")
    agg_stats_str = " | ".join(agg_stats_parts) if agg_stats_parts else "match stats not yet available"

    # ---- Deep shot-level analytics via DataProvider ----
    from Api.services.football_providers import get_provider
    from Api.services import football_insights as fi

    provider = get_provider()
    deep_matches = recent[-5:]  # last 5 for shot-level detail
    insights_text = ""
    danger = []
    alerts: list[str] = []
    goals_log_for: list[str] = []
    goals_log_against: list[str] = []
    circ_for = circ_against = {}
    viz_payload: dict = {}
    try:
        shots = provider.get_shot_events(deep_matches, req.team)
        goals = provider.get_goal_events(deep_matches, req.team)
        goals_log_for = fi.goal_log(goals, is_for=True)
        goals_log_against = fi.goal_log(goals, is_for=False)
        danger = fi.player_danger_scores(shots, goals, top=3)
        circ_for = fi.goal_circumstances(goals, is_for=True)
        circ_against = fi.goal_circumstances(goals, is_for=False)
        set_pieces = fi.set_piece_breakdown(goals)
        tend_for = fi.shot_tendencies(shots, is_for=True)
        tend_against = fi.shot_tendencies(shots, is_for=False)
        alerts = fi.key_alerts(shots, goals, danger, circ_for, tend_against, lang=req.language)
        lineup = provider.get_lineups(deep_matches, req.team)
        formation = {}
        if hasattr(provider, "get_formation"):
            formation = provider.get_formation(deep_matches, req.team)
        per_match_formation = (provider.get_formation_per_match(deep_matches, req.team)
                               if hasattr(provider, "get_formation_per_match") else [])
        tact_evo = fi.tactical_evolution(per_match_formation)
        insights_text = fi.insights_to_text(
            danger, circ_for, circ_against, set_pieces,
            tend_for, tend_against, provider.has_xg,
        )
        # Persist raw data so the PDF endpoint can render shot maps / timing.
        viz_payload = {
            "shots": shots,
            "goal_minutes_for": fi.goal_minutes(goals, is_for=True),
            "goal_minutes_against": fi.goal_minutes(goals, is_for=False),
            "has_xg": provider.has_xg,
            "provider": provider.name,
            "lineup": [name for name, _ in lineup],
            "formation": formation,
        }
    except Exception as exc:
        insights_text = f"(Shot-level analytics unavailable: {exc})"
        tact_evo = {}

    recent_str = "\n".join(f"  {_fmt_match(m, req.team, neutral)}" for m in recent) or "  no data"
    extra = f"\n\nADDITIONAL NOTES:\n{req.extra_notes}" if req.extra_notes.strip() else ""

    # Competition rankings — turns loose numbers into standing ("worst defence")
    ranks = team_rankings(req.team, standings, lang=req.language)
    ranks_block = _rankings_text(ranks, req.team, lang=req.language)

    comp_label = _COMPS[comp]["label"]
    raw_stats = "\n".join([
        f"TEAM: {stats_str}",
        f"FORM (last {len(recent)}): {form}",
        f"LOCATION SPLIT: {location_breakdown}",
        f"AGGREGATED MATCH STATS: {agg_stats_str}",
        "",
        ranks_block,
        "",
        "=== SHOT-LEVEL ANALYTICS (last 5 matches) ===",
        insights_text,
        "",
        f"LAST {len(recent)} MATCHES (scorers + per-match stats where available):",
        recent_str,
    ])

    lang = req.language
    lang_instruction = (
        "CRITICAL INSTRUCTION: You MUST write every single word of your response in Brazilian Portuguese. "
        "This includes ALL JSON string values — executive_summary, playing_style, every list item, everything. "
        "Do NOT write any English. Use football terminology standard in Brazil."
        if lang == "pt"
        else "Write the entire report in English."
    )

    prompt = f"""You are an experienced assistant coach briefing your head coach and staff on the next opponent.

LANGUAGE: {lang_instruction}

{_comp_context(comp)}

TEAM BEING SCOUTED: {req.team}

=== DATA SOURCE: ESPN {comp_label} ===

{raw_stats}{extra}

VOICE & STYLE — write like a coach, not an AI:
- Direct, concrete, confident. Short sentences. Imperative where it fits ("Double up on their left-back", "Don't let #6 turn").
- BANNED phrasing: "exhibits", "showcases", "boasts a balanced style", "demonstrates", "it is worth noting", "overall".
  Never describe a team as "balanced" or "solid" without a number behind it.
- Every claim cites evidence from the data — a name, a %, a count, a scoreline. No generic filler.
- Talk about players by name. Talk about specific zones, minutes, and situations.

ANALYSIS INSTRUCTIONS:
- The data includes: results, goal scorers with times, possession %, shots on target/total, corners, yellow cards, shot sides.
- Infer style from numbers: high possession = ball-dominant; many shots but few on target = wasteful; central shots conceded = soft middle.
- Name the dangerous players. Pin patterns to evidence (e.g. "scores from the right channel — 3 of last 5 goals from there").
- "how_to_beat_them" must read like a game-plan a coach hands to players — specific, named, actionable.

SMALL-SAMPLE RULE (critical for credibility):
- If the team has played fewer than 3 matches OR scored fewer than 3 goals, NEVER use percentages for goal types.
- Use absolute counts instead ("1 of 1 goal came from a corner") and explicitly flag the limited sample.
- NEVER write "100%" off one or two goals. A coach distrusts a report that says "100% from set pieces" after one match.

Return EXACTLY this JSON (no extra keys, no markdown):
{{
  "executive_summary": "MILITARY LABEL STYLE: exactly 4-5 lines, each a LABEL in CAPS followed by a colon and a short value, separated by newline characters (\\n). Use these labels: STYLE, MAIN THREAT, KEY WEAKNESS, DANGER PERIOD (and optionally SET PIECES). Example: 'STYLE: Ball-dominant (55% possession)\\nMAIN THREAT: Cody Gakpo (2G 1A)\\nKEY WEAKNESS: Concedes from corners\\nDANGER PERIOD: 46-60''. Each value short and concrete. No prose sentences.",
  "playing_style": "2-3 sentences: inferred style from possession, shots, and results — are they dominant or reactive?",
  "strengths": ["specific data-backed strength with evidence 1", "strength 2", "strength 3"],
  "weaknesses": ["exploitable weakness with evidence 1", "weakness 2", "weakness 3"],
  "key_patterns": ["concrete pattern from data (e.g. scorer, timing, set pieces) 1", "pattern 2", "pattern 3"],
  "how_to_beat_them": ["specific named instruction based on a weakness 1", "instruction 2", "instruction 3"],
  "pressing_vulnerabilities": ["specific moment/zone where they can be pressed, with evidence 1", "vulnerability 2"],
  "set_piece_tendencies": ["corner/free kick insight from data 1", "observation 2"],
  "form_analysis": "2-3 sentences on recent form string — are they improving, declining, or inconsistent?"
}}"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0.15,
    )

    raw = json.loads(resp.choices[0].message.content or "{}")

    def to_list(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    comp_label = _COMPS.get(comp, _COMPS["serie_a"])["label"]
    source = f"{comp_label} Dataset ({len(schedule)} fixtures)"
    if not row:
        source += f" | WARNING: '{req.team}' not matched in standings"

    # Human-readable circumstance lines (small-sample aware: counts not %)
    how_score = fi.fmt_circumstance(circ_for, lang=req.language, matches_analysed=len(deep_matches))
    how_concede = fi.fmt_circumstance(circ_against, lang=req.language, matches_analysed=len(deep_matches))

    # Render charts as base64 for inline web display (safe, optional)
    images: dict = {}
    if viz_payload:
        try:
            from Api.services import football_viz as fv
            images = fv.render_scout_images(viz_payload, req.team)
        except Exception:
            images = {}

    return OpponentScoutReport(
        team=req.team,
        data_source=source,
        executive_summary=str(raw.get("executive_summary", "")).strip(),
        playing_style=str(raw.get("playing_style", "")).strip(),
        strengths=to_list(raw.get("strengths")),
        weaknesses=to_list(raw.get("weaknesses")),
        key_patterns=to_list(raw.get("key_patterns")),
        how_to_beat_them=to_list(raw.get("how_to_beat_them")),
        pressing_vulnerabilities=to_list(raw.get("pressing_vulnerabilities")),
        set_piece_tendencies=to_list(raw.get("set_piece_tendencies")),
        form_analysis=str(raw.get("form_analysis", "")).strip(),
        raw_stats_used=raw_stats,
        top_danger_players=danger,
        key_alerts=alerts,
        goals_log_for=goals_log_for,
        goals_log_against=goals_log_against,
        how_they_score=how_score,
        how_they_concede=how_concede,
        probable_lineup=viz_payload.get("lineup", []),
        has_xg=bool(viz_payload.get("has_xg", False)),
        tactical_evolution=tact_evo,
        competition_ranks=ranks,
        viz_payload=viz_payload,
        images=images,
    )


# ---------------------------------------------------------------------------
# Legacy single-team report (kept for backward compat)
# ---------------------------------------------------------------------------

def generate_opponent_report(payload: FootballAnalyzeRequest) -> FootballAnalyzeResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    system = (
        "You are a senior football opposition analyst. "
        "Use only the stats and observations supplied. "
        "Return concise, practical coaching language as valid JSON only."
    )
    user = f"""Create an opponent analysis for: {payload.team_name}

Stats:
{payload.stats or 'No stats provided.'}

Observations:
{payload.observations or 'No observations provided.'}

Return JSON:
{{
  "executive_summary": "2-4 sentence overview",
  "tactical_strengths": ["strength 1", "strength 2"],
  "tactical_weaknesses": ["weakness 1", "weakness 2"],
  "key_players_to_watch": ["player 1", "player 2"],
  "recommended_match_strategy": "clear match plan",
  "pressing_recommendations": ["trigger 1", "trigger 2"],
  "set_piece_considerations": ["note 1", "note 2"],
  "risk_assessment": "risks and mitigation"
}}"""

    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.25,
    )
    raw = json.loads(resp.choices[0].message.content or "{}")

    def cl(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    return FootballAnalyzeResponse(
        team_name=payload.team_name.strip(),
        report=FootballAnalysisReport(
            executive_summary=str(raw.get("executive_summary", "")).strip(),
            tactical_strengths=cl(raw.get("tactical_strengths")),
            tactical_weaknesses=cl(raw.get("tactical_weaknesses")),
            key_players_to_watch=cl(raw.get("key_players_to_watch")),
            recommended_match_strategy=str(raw.get("recommended_match_strategy", "")).strip(),
            pressing_recommendations=cl(raw.get("pressing_recommendations")),
            set_piece_considerations=cl(raw.get("set_piece_considerations")),
            risk_assessment=str(raw.get("risk_assessment", "")).strip(),
        ),
    )
