from __future__ import annotations

import json
import os
from urllib.parse import quote

import requests
from pydantic import BaseModel, Field


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


def _system_prompt() -> str:
    return (
        "You are a senior football opposition analyst helping coaches prepare match plans. "
        "Use only the team name, stats, and raw observations supplied by the user. "
        "If information is missing, state the uncertainty inside the relevant section instead of inventing facts. "
        "Return concise, practical coaching language. "
        "Output valid JSON only."
    )


def _sportsdb_key() -> str:
    return os.getenv("THESPORTSDB_API_KEY") or "123"


def _sportsdb_get(path: str) -> dict:
    url = f"https://www.thesportsdb.com/api/v1/json/{_sportsdb_key()}/{path}"
    response = requests.get(url, timeout=12)
    response.raise_for_status()
    return response.json()


def _pick_soccer_team(teams: list[dict] | None) -> dict | None:
    for team in teams or []:
        if (team.get("strSport") or "").lower() == "soccer":
            return team
    return (teams or [None])[0]


def _format_event(event: dict, team_name: str) -> str:
    home = event.get("strHomeTeam") or "Home"
    away = event.get("strAwayTeam") or "Away"
    home_score = event.get("intHomeScore")
    away_score = event.get("intAwayScore")
    date = event.get("dateEvent") or "date unknown"
    league = event.get("strLeague") or "competition unknown"
    score = f"{home_score}-{away_score}" if home_score is not None and away_score is not None else "score unavailable"
    venue = "home" if home.lower() == team_name.lower() else ("away" if away.lower() == team_name.lower() else "neutral/unknown")
    return f"{date} | {league} | {home} {score} {away} | {venue}"


def fetch_team_context(team_name: str) -> FootballTeamContext:
    clean_name = team_name.strip()
    if not clean_name:
        raise ValueError("team_name is required")

    search = _sportsdb_get(f"searchteams.php?t={quote(clean_name)}")
    team = _pick_soccer_team(search.get("teams"))
    if not team:
        raise LookupError(f"No football team found for '{clean_name}'")

    resolved_name = team.get("strTeam") or clean_name
    team_id = team.get("idTeam")
    league = team.get("strLeague") or "Unknown league"
    country = team.get("strCountry") or "Unknown country"
    stadium = team.get("strStadium") or "Unknown stadium"
    formed = team.get("intFormedYear") or "Unknown"
    description = (team.get("strDescriptionEN") or "").strip()

    last_events: list[dict] = []
    next_events: list[dict] = []
    players: list[dict] = []
    if team_id:
        try:
            last_events = (_sportsdb_get(f"eventslast.php?id={team_id}").get("results") or [])[:5]
        except requests.RequestException:
            last_events = []
        try:
            next_events = (_sportsdb_get(f"eventsnext.php?id={team_id}").get("events") or [])[:3]
        except requests.RequestException:
            next_events = []
        try:
            players = (_sportsdb_get(f"lookup_all_players.php?id={team_id}").get("player") or [])[:8]
        except requests.RequestException:
            players = []

    lines = [
        f"Team: {resolved_name}",
        f"Country: {country}",
        f"League: {league}",
        f"Stadium: {stadium}",
        f"Founded: {formed}",
    ]

    if last_events:
        lines.append("")
        lines.append("Recent matches:")
        lines.extend(f"- {_format_event(event, resolved_name)}" for event in last_events)

    if next_events:
        lines.append("")
        lines.append("Upcoming matches:")
        lines.extend(f"- {_format_event(event, resolved_name)}" for event in next_events)

    if players:
        lines.append("")
        lines.append("Listed squad sample:")
        for player in players:
            name = player.get("strPlayer") or "Unknown player"
            position = player.get("strPosition") or "Unknown position"
            nationality = player.get("strNationality") or "Unknown nationality"
            lines.append(f"- {name} | {position} | {nationality}")

    observations = ""
    if description:
        short_description = description[:1200].rsplit(".", 1)[0]
        observations = (
            "Automatic public-data note: this is club/context data, not tactical scouting. "
            "Add match observations for pressing, build-up, transitions and set pieces.\n\n"
            f"Club context: {short_description}."
        )
    else:
        observations = (
            "Automatic public-data note: only basic team/event data was found. "
            "Add human match observations before generating a serious tactical report."
        )

    return FootballTeamContext(
        team_name=resolved_name,
        source="TheSportsDB",
        stats="\n".join(lines),
        observations=observations,
    )


def _user_prompt(payload: FootballAnalyzeRequest) -> str:
    return f"""
Create an opponent analysis report for: {payload.team_name}

Raw statistics:
{payload.stats or "No structured stats provided."}

Raw match observations:
{payload.observations or "No observations provided."}

Return this JSON object exactly:
{{
  "executive_summary": "2-4 sentence overview",
  "tactical_strengths": ["strength 1", "strength 2", "strength 3"],
  "tactical_weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "key_players_to_watch": ["player or role 1", "player or role 2"],
  "recommended_match_strategy": "clear match plan",
  "pressing_recommendations": ["pressing trigger 1", "pressing trigger 2"],
  "set_piece_considerations": ["set piece note 1", "set piece note 2"],
  "risk_assessment": "main risks and mitigation"
}}
""".strip()


def _coerce_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalise_report(raw: dict) -> FootballAnalysisReport:
    return FootballAnalysisReport(
        executive_summary=str(raw.get("executive_summary") or "").strip(),
        tactical_strengths=_coerce_list(raw.get("tactical_strengths")),
        tactical_weaknesses=_coerce_list(raw.get("tactical_weaknesses")),
        key_players_to_watch=_coerce_list(raw.get("key_players_to_watch")),
        recommended_match_strategy=str(raw.get("recommended_match_strategy") or "").strip(),
        pressing_recommendations=_coerce_list(raw.get("pressing_recommendations")),
        set_piece_considerations=_coerce_list(raw.get("set_piece_considerations")),
        risk_assessment=str(raw.get("risk_assessment") or "").strip(),
    )


def generate_opponent_report(payload: FootballAnalyzeRequest) -> FootballAnalyzeResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": _user_prompt(payload)},
        ],
        temperature=0.25,
    )

    content = response.choices[0].message.content or "{}"
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("OpenAI returned invalid JSON") from exc

    return FootballAnalyzeResponse(
        team_name=payload.team_name.strip(),
        report=_normalise_report(raw),
    )
