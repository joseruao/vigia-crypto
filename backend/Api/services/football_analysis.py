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
    how_they_score: list[str] = Field(default_factory=list)
    how_they_concede: list[str] = Field(default_factory=list)
    probable_lineup: list[str] = Field(default_factory=list)
    has_xg: bool = False
    # Raw viz payload for PDF chart rendering (frontend ignores it)
    viz_payload: dict = Field(default_factory=dict)


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
    h2h_str = (
        "\n".join(
            f"  {m['date']} | {m['home']} {m.get('score','?')} {m['away']}"
            for m in h2h
        )
        or "  no H2H matches found this season"
    )

    comp_label = _COMPS[comp]["label"]
    raw_stats = "\n".join([
        f"MY TEAM [{my_form}]:  {my_stats_str}",
        f"OPPONENT [{opp_form}]: {opp_stats_str}",
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

ANALYSIS INSTRUCTIONS:
- Work ONLY from the data above. Do not invent stats or players.
- The match data includes: result, goal scorers with times, possession %, shots on target/total, corners, yellow cards.
- Use goal scorers to identify key threats by name.
- Use possession and shots data to infer playing style (high possession = controlled play, low shots = defensive).
- Use corners data for set piece analysis.
- Calculate patterns from results: goals scored/conceded per game, winning/losing streaks, form trajectory.
- Be concrete and coaching-practical — name patterns with evidence (e.g. "conceded in 3 of last 4 matches from set pieces").
- If match stats are not available for some games, note it and work with what you have.

Return EXACTLY this JSON (no extra keys, no markdown):
{{
  "executive_summary": "3-4 sentences: current form of both teams, what the stats say about this matchup, key tactical context",
  "opponent_strengths": ["data-backed strength with evidence 1", "strength 2", "strength 3"],
  "opponent_weaknesses": ["exploitable weakness with evidence 1", "weakness 2", "weakness 3"],
  "key_threats": ["named player or pattern to neutralise, with evidence 1", "threat 2"],
  "tactical_approach": "2-3 sentences: concrete game plan based on the data — how to set up, what to exploit",
  "pressing_triggers": ["specific moment/situation to press 1", "trigger 2"],
  "attacking_approach": ["specific attacking instruction based on opponent weakness 1", "instruction 2", "instruction 3"],
  "set_piece_plan": ["set piece insight from corners/free kicks data 1", "consideration 2"],
  "risk_assessment": "main risks in this specific matchup and how to mitigate them"
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
    source = f"ESPN {comp_label} ({len(schedule)} fixtures, {len(standings)} teams)"
    if warnings:
        source += " | " + " | ".join(warnings)

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
    circ_for = circ_against = {}
    viz_payload: dict = {}
    try:
        shots = provider.get_shot_events(deep_matches, req.team)
        goals = provider.get_goal_events(deep_matches, req.team)
        danger = fi.player_danger_scores(shots, goals, top=3)
        circ_for = fi.goal_circumstances(goals, is_for=True)
        circ_against = fi.goal_circumstances(goals, is_for=False)
        set_pieces = fi.set_piece_breakdown(goals)
        tend_for = fi.shot_tendencies(shots, is_for=True)
        tend_against = fi.shot_tendencies(shots, is_for=False)
        lineup = provider.get_lineups(deep_matches, req.team)
        formation = {}
        if hasattr(provider, "get_formation"):
            formation = provider.get_formation(deep_matches, req.team)
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

    recent_str = "\n".join(f"  {_fmt_match(m, req.team, neutral)}" for m in recent) or "  no data"
    extra = f"\n\nADDITIONAL NOTES:\n{req.extra_notes}" if req.extra_notes.strip() else ""

    comp_label = _COMPS[comp]["label"]
    raw_stats = "\n".join([
        f"TEAM: {stats_str}",
        f"FORM (last {len(recent)}): {form}",
        f"LOCATION SPLIT: {location_breakdown}",
        f"AGGREGATED MATCH STATS: {agg_stats_str}",
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

    prompt = f"""You are a senior football scout preparing a deep opposition report for a professional coaching staff.

LANGUAGE: {lang_instruction}

{_comp_context(comp)}

TEAM BEING SCOUTED: {req.team}

=== DATA SOURCE: ESPN {comp_label} ===

{raw_stats}{extra}

ANALYSIS INSTRUCTIONS:
- Focus entirely on {req.team}. No "my team" context needed here.
- The data includes: match results, goal scorers with times (use to identify top scorers and goal timing patterns),
  per-match possession %, shots on target/total (use to infer style), corners (set piece volume), yellow cards (aggression).
- Use aggregated stats to infer playing style: high possession = ball-dominant; high shots off target = wasteful finishing.
- Use corner count to infer set piece danger. Use YC rate to infer defensive aggressiveness.
- Identify specific scorers from the data — name them in key_patterns and how_to_beat_them where relevant.
- "how_to_beat_them" must be specific, named, and data-driven — NOT generic advice like "press high".
- If data is limited (few matches), be honest about it — do not extrapolate beyond what the data supports.

Return EXACTLY this JSON (no extra keys, no markdown):
{{
  "executive_summary": "3-4 sentences: season overview, form trajectory, what the stats reveal about this team",
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
    source = f"ESPN {comp_label} ({len(schedule)} fixtures)"
    if not row:
        source += f" | WARNING: '{req.team}' not matched in standings"

    # Human-readable circumstance lines for the frontend/PDF text sections
    how_score = [f"{b['type']}: {b['pct']}%" for b in circ_for.get("breakdown", [])]
    how_concede = [f"{b['type']}: {b['pct']}%" for b in circ_against.get("breakdown", [])]

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
        how_they_score=how_score,
        how_they_concede=how_concede,
        probable_lineup=viz_payload.get("lineup", []),
        has_xg=bool(viz_payload.get("has_xg", False)),
        viz_payload=viz_payload,
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
