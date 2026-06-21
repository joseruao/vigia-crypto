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
    my_team: str = Field(..., min_length=1, max_length=120, description="Your team, e.g. 'Cruzeiro'")
    opponent_team: str = Field(..., min_length=1, max_length=120, description="Opponent, e.g. 'Flamengo'")
    extra_notes: str = Field(default="", max_length=5000, description="Optional coach observations")
    language: str = Field(default="en", pattern="^(en|pt)$", description="Report language: en or pt")


class OpponentScoutRequest(BaseModel):
    team: str = Field(..., min_length=1, max_length=120, description="Team to scout, e.g. 'Flamengo'")
    extra_notes: str = Field(default="", max_length=5000)
    language: str = Field(default="en", pattern="^(en|pt)$")


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

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1"
_ESPN_STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/bra.1/standings"
_ESPN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL = int(os.getenv("FOOTBALL_CACHE_TTL_SECONDS", "1800"))  # 30 min


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

def _fetch_standings_raw() -> list[dict]:
    data = _get(_ESPN_STANDINGS)
    entries = (
        data.get("children", [data])[0]
        .get("standings", data.get("standings", {}))
        .get("entries", [])
    )
    rows = []
    for entry in entries:
        team = entry.get("team", {})
        stats_map = {}
        for s in entry.get("stats", []):
            if "value" in s:
                stats_map[s["name"]] = s["value"]
        rows.append({
            "team": team.get("displayName", ""),
            "abbr": team.get("abbreviation", ""),
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
    return sorted(rows, key=lambda r: r["rank"])


def _fetch_season_matches_raw() -> list[dict]:
    year = time.strftime("%Y")
    data = _get(
        f"{_ESPN_BASE}/scoreboard",
        params={"dates": f"{year}0101-{year}1231", "limit": 400},
    )
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
            "date": ev.get("date", "")[:10],
            "home": home.get("team", {}).get("displayName", ""),
            "away": away.get("team", {}).get("displayName", ""),
            "score": score,
            "status": status,
            "round": comp.get("series", {}).get("title") or ev.get("season", {}).get("displayName", ""),
        })
    return matches


def fetch_serie_a_standings() -> list[dict]:
    return _cached("standings", _fetch_standings_raw)


def fetch_serie_a_schedule() -> list[dict]:
    return _cached("schedule", _fetch_season_matches_raw)


def list_serie_a_teams() -> list[str]:
    return [r["team"] for r in fetch_serie_a_standings()]


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


def _fmt_match(m: dict, perspective: str) -> str:
    score = m.get("score") or "upcoming"
    venue = "HOME" if _teams_match(perspective, m["home"]) else "AWAY"
    result = ""
    if m.get("score"):
        h, a = m["score"].split("-")
        h, a = int(h), int(a)
        if _teams_match(perspective, m["home"]):
            result = "W" if h > a else ("D" if h == a else "L")
        else:
            result = "W" if a > h else ("D" if h == a else "L")
    return f"{m['date']} | {m['home']} {score} {m['away']} | {venue} {result}"


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
    standings = fetch_serie_a_standings()
    schedule = fetch_serie_a_schedule()

    my_row = _find_team_row(req.my_team, standings)
    opp_row = _find_team_row(req.opponent_team, standings)
    my_recent = _team_recent(req.my_team, schedule)
    opp_recent = _team_recent(req.opponent_team, schedule)
    h2h = _head_to_head(req.my_team, req.opponent_team, schedule)

    my_stats_str = _fmt_standing(my_row) if my_row else f"{req.my_team}: NOT FOUND in current standings"
    opp_stats_str = _fmt_standing(opp_row) if opp_row else f"{req.opponent_team}: NOT FOUND in current standings"
    my_form = _form_string(req.my_team, my_recent)
    opp_form = _form_string(req.opponent_team, opp_recent)

    my_recent_str = "\n".join(f"  {_fmt_match(m, req.my_team)}" for m in my_recent) or "  no data"
    opp_recent_str = "\n".join(f"  {_fmt_match(m, req.opponent_team)}" for m in opp_recent) or "  no data"
    h2h_str = (
        "\n".join(
            f"  {m['date']} | {m['home']} {m.get('score','?')} {m['away']}"
            for m in h2h
        )
        or "  no H2H matches found this season"
    )

    raw_stats = "\n".join([
        f"MY TEAM [{my_form}]:  {my_stats_str}",
        f"OPPONENT [{opp_form}]: {opp_stats_str}",
        "",
        f"MY TEAM — LAST {len(my_recent)} MATCHES:",
        my_recent_str,
        "",
        f"OPPONENT — LAST {len(opp_recent)} MATCHES:",
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

    prompt = f"""You are the lead analyst for a professional football club competing in the Campeonato Brasileiro Série A.
The head coach needs a match preparation report before the next game.

LANGUAGE: {lang_instruction}

MY TEAM: {req.my_team}
OPPONENT: {req.opponent_team}

=== DATA SOURCE: ESPN (Série A {time.strftime('%Y')}) ===

{raw_stats}{extra}

ANALYSIS INSTRUCTIONS:
- Work ONLY from the data above. Do not invent stats.
- Calculate patterns: goals scored/conceded per game, home vs away performance, winning/losing streaks, form trajectory.
- Identify exploitable patterns vs the opponent (e.g. "opponent concedes 2+ in 4 of last 6 away games").
- Be concrete and practical — this report goes directly to the coaching staff.
- If data for a team is missing, acknowledge it briefly and work with what you have.

Return EXACTLY this JSON (no extra keys, no markdown):
{{
  "executive_summary": "3-4 sentences: current form of both teams, what the numbers say about this matchup, tactical context",
  "opponent_strengths": ["data-backed strength 1", "strength 2", "strength 3"],
  "opponent_weaknesses": ["exploitable weakness from data 1", "weakness 2", "weakness 3"],
  "key_threats": ["specific threat or player pattern to neutralise 1", "threat 2"],
  "tactical_approach": "2-3 sentences: game plan — how to approach this game given the data (high block? press? possession?)",
  "pressing_triggers": ["specific situation to press hard 1", "trigger 2"],
  "attacking_approach": ["attacking instruction based on opponent weakness 1", "instruction 2", "instruction 3"],
  "set_piece_plan": ["set piece consideration based on data 1", "consideration 2"],
  "risk_assessment": "main risks in this specific game and how to mitigate them"
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

    source = f"ESPN Série A {time.strftime('%Y')} ({len(schedule)} fixtures, {len(standings)} teams)"
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
    standings = fetch_serie_a_standings()
    schedule = fetch_serie_a_schedule()

    row = _find_team_row(req.team, standings)
    recent = _team_recent(req.team, schedule, n=10)

    stats_str = _fmt_standing(row) if row else f"{req.team}: NOT FOUND in current standings"
    form = _form_string(req.team, recent)

    home_matches = [m for m in recent if _teams_match(req.team, m["home"])]
    away_matches = [m for m in recent if _teams_match(req.team, m["away"])]

    def goals_for(matches, team):
        totals = []
        for m in matches:
            if not m.get("score"):
                continue
            h, a = m["score"].split("-")
            totals.append(int(h) if _teams_match(team, m["home"]) else int(a))
        return totals

    def goals_against(matches, team):
        totals = []
        for m in matches:
            if not m.get("score"):
                continue
            h, a = m["score"].split("-")
            totals.append(int(a) if _teams_match(team, m["home"]) else int(h))
        return totals

    home_gf = goals_for(home_matches, req.team)
    home_ga = goals_against(home_matches, req.team)
    away_gf = goals_for(away_matches, req.team)
    away_ga = goals_against(away_matches, req.team)

    def avg(lst): return round(sum(lst) / len(lst), 2) if lst else 0.0

    home_away_breakdown = (
        f"HOME ({len(home_matches)} games): avg {avg(home_gf)} scored / {avg(home_ga)} conceded | "
        f"AWAY ({len(away_matches)} games): avg {avg(away_gf)} scored / {avg(away_ga)} conceded"
    )

    recent_str = "\n".join(f"  {_fmt_match(m, req.team)}" for m in recent) or "  no data"
    extra = f"\n\nADDITIONAL NOTES:\n{req.extra_notes}" if req.extra_notes.strip() else ""

    raw_stats = "\n".join([
        f"TEAM: {stats_str}",
        f"FORM (last {len(recent)}): {form}",
        f"HOME/AWAY: {home_away_breakdown}",
        "",
        f"LAST {len(recent)} MATCHES:",
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

    prompt = f"""You are a senior football scout preparing a deep opposition report for a coaching staff in the Campeonato Brasileiro Série A.

LANGUAGE: {lang_instruction}

TEAM BEING SCOUTED: {req.team}

=== DATA SOURCE: ESPN (Série A {time.strftime('%Y')}) ===

{raw_stats}{extra}

ANALYSIS INSTRUCTIONS:
- This is a standalone deep scout — there is no "my team" context. Focus entirely on {req.team}.
- Calculate home vs away split carefully — teams often have very different profiles at home vs away.
- Identify concrete patterns: do they score early? concede in the final 15? struggle on the road?
- "how_to_beat_them" must be specific and data-driven, not generic advice.
- pressing_vulnerabilities should identify when/where they can be pressed based on their results.
- If data is limited, say so clearly — do not invent numbers.

Return EXACTLY this JSON (no extra keys, no markdown):
{{
  "executive_summary": "3-4 sentences covering their season overall, form trajectory, and what kind of team they are",
  "playing_style": "2-3 sentences describing their likely style based on goals, home/away data, and results patterns",
  "strengths": ["data-backed strength 1", "strength 2", "strength 3"],
  "weaknesses": ["exploitable weakness 1", "weakness 2", "weakness 3"],
  "key_patterns": ["notable pattern from results data 1", "pattern 2", "pattern 3"],
  "how_to_beat_them": ["specific instruction 1", "instruction 2", "instruction 3"],
  "pressing_vulnerabilities": ["where/when to press them 1", "vulnerability 2"],
  "set_piece_tendencies": ["set piece observation 1", "observation 2"],
  "form_analysis": "2-3 sentences analysing their recent form string and what it reveals about their current momentum"
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

    source = f"ESPN Série A {time.strftime('%Y')} ({len(schedule)} fixtures)"
    if not row:
        source += f" | WARNING: '{req.team}' not matched in standings"

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
