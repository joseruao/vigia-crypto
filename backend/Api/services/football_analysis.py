from __future__ import annotations

import json
import os
from datetime import date
from datetime import timedelta
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


def _api_football_key() -> str | None:
    return os.getenv("API_FOOTBALL_KEY") or os.getenv("APISPORTS_KEY")


def _api_football_get(path: str, params: dict | None = None) -> dict:
    api_key = _api_football_key()
    if not api_key:
        raise RuntimeError("API_FOOTBALL_KEY is not configured")

    response = requests.get(
        f"https://v3.football.api-sports.io/{path}",
        headers={"x-apisports-key": api_key},
        params=params or {},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


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


def _pick_api_football_team(items: list[dict] | None) -> tuple[dict, dict] | None:
    for item in items or []:
        team = item.get("team") or {}
        if (team.get("name") or "").strip():
            return team, item.get("venue") or {}
    return None


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


def _format_api_football_fixture(fixture: dict, team_id: int | None = None) -> str:
    fixture_meta = fixture.get("fixture") or {}
    league = fixture.get("league") or {}
    teams = fixture.get("teams") or {}
    goals = fixture.get("goals") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    venue = fixture_meta.get("venue") or {}
    status = (fixture_meta.get("status") or {}).get("short") or "unknown"
    played_where = "home" if home.get("id") == team_id else ("away" if away.get("id") == team_id else "neutral/unknown")
    score = (
        f"{goals.get('home')}-{goals.get('away')}"
        if goals.get("home") is not None and goals.get("away") is not None
        else "score unavailable"
    )
    return (
        f"{(fixture_meta.get('date') or '')[:10]} | {league.get('name') or 'competition unknown'} | "
        f"{home.get('name') or 'Home'} {score} {away.get('name') or 'Away'} | "
        f"{played_where} | status {status} | venue {venue.get('name') or 'unknown'}"
    )


def _pick_latest_competition(leagues: list[dict] | None) -> tuple[dict, dict] | None:
    league_priority_terms = ("liga", "league", "serie", "premier", "la liga", "bundesliga", "ligue")
    candidates: list[tuple[int, int, dict, dict]] = []
    for item in leagues or []:
        league = item.get("league") or {}
        league_name = (league.get("name") or "").lower()
        league_type = (league.get("type") or "").lower()
        priority = 1 if league_type == "league" or any(term in league_name for term in league_priority_terms) else 0
        seasons = item.get("seasons") or []
        for season in seasons:
            year = season.get("year")
            if year:
                current_bonus = 10_000 if season.get("current") else 0
                candidates.append((priority, int(year) + current_bonus, league, season))
    if not candidates:
        return None
    _priority, _score, league, season = max(candidates, key=lambda item: (item[0], item[1]))
    return league, season


def _stats_played_total(stats: dict) -> int:
    try:
        return int((((stats.get("fixtures") or {}).get("played") or {}).get("total")) or 0)
    except (TypeError, ValueError):
        return 0


def _season_candidates(preferred: int | None, current: int) -> list[int]:
    candidates = []
    for value in [preferred, current, current - 1, current - 2, current - 3]:
        if value and value not in candidates:
            candidates.append(int(value))
    return candidates


def _format_team_statistics(stats: dict) -> list[str]:
    if not stats:
        return []

    fixtures = stats.get("fixtures") or {}
    goals = stats.get("goals") or {}
    clean_sheet = stats.get("clean_sheet") or {}
    failed_to_score = stats.get("failed_to_score") or {}
    cards = stats.get("cards") or {}
    biggest = stats.get("biggest") or {}

    played = (fixtures.get("played") or {}).get("total")
    wins = (fixtures.get("wins") or {}).get("total")
    draws = (fixtures.get("draws") or {}).get("total")
    loses = (fixtures.get("loses") or {}).get("total")
    goals_for = ((goals.get("for") or {}).get("total") or {}).get("total")
    goals_against = ((goals.get("against") or {}).get("total") or {}).get("total")
    avg_for = ((goals.get("for") or {}).get("average") or {}).get("total")
    avg_against = ((goals.get("against") or {}).get("average") or {}).get("total")
    clean_total = (clean_sheet or {}).get("total")
    failed_total = (failed_to_score or {}).get("total")

    lines = [
        f"- Record: played {played or 0}, wins {wins or 0}, draws {draws or 0}, losses {loses or 0}",
        f"- Goals: scored {goals_for or 0} ({avg_for or 'n/a'} avg), conceded {goals_against or 0} ({avg_against or 'n/a'} avg)",
        f"- Clean sheets: {clean_total or 0}; failed to score: {failed_total or 0}",
    ]

    streak = biggest.get("streak") or {}
    if streak:
        lines.append(
            f"- Streaks: wins {streak.get('wins') or 0}, draws {streak.get('draws') or 0}, losses {streak.get('loses') or 0}"
        )

    card_total = 0
    for colour in ("yellow", "red"):
        for bucket in (cards.get(colour) or {}).values():
            card_total += int((bucket or {}).get("total") or 0)
    if card_total:
        lines.append(f"- Cards total: {card_total}")

    return lines


def _format_standings(standings: list[dict], team_id: int | None = None) -> list[str]:
    rows = []
    for league_group in standings or []:
        for row in league_group or []:
            team = row.get("team") or {}
            if team_id and team.get("id") != team_id:
                continue
            all_stats = row.get("all") or {}
            goals = all_stats.get("goals") or {}
            rows.append(
                f"- Rank {row.get('rank') or 'n/a'} | {team.get('name') or 'Unknown'} | "
                f"points {row.get('points') or 0} | played {all_stats.get('played') or 0} | "
                f"W-D-L {all_stats.get('win') or 0}-{all_stats.get('draw') or 0}-{all_stats.get('lose') or 0} | "
                f"GF {goals.get('for') or 0} / GA {goals.get('against') or 0} | form {row.get('form') or 'n/a'}"
            )
    return rows


def _format_fixture_statistics(stats: list[dict]) -> list[str]:
    wanted = {
        "Shots on Goal",
        "Shots off Goal",
        "Total Shots",
        "Blocked Shots",
        "Shots insidebox",
        "Shots outsidebox",
        "Fouls",
        "Corner Kicks",
        "Offsides",
        "Ball Possession",
        "Yellow Cards",
        "Red Cards",
        "Goalkeeper Saves",
        "Total passes",
        "Passes accurate",
        "Passes %",
        "expected_goals",
    }
    lines: list[str] = []
    for team_stats in stats or []:
        team = (team_stats.get("team") or {}).get("name") or "Team"
        values = []
        for item in team_stats.get("statistics") or []:
            stat_type = item.get("type")
            value = item.get("value")
            if stat_type in wanted and value is not None:
                values.append(f"{stat_type}: {value}")
        if values:
            lines.append(f"- {team}: " + " | ".join(values[:12]))
    return lines


def _format_lineups(lineups: list[dict]) -> list[str]:
    lines = []
    for lineup in lineups or []:
        team = lineup.get("team") or {}
        coach = lineup.get("coach") or {}
        start_xi = lineup.get("startXI") or []
        players = []
        for item in start_xi[:11]:
            player = item.get("player") or {}
            name = player.get("name")
            pos = player.get("pos")
            if name:
                players.append(f"{name}{f' ({pos})' if pos else ''}")
        lines.append(
            f"- {team.get('name') or 'Unknown team'} | formation {lineup.get('formation') or 'unknown'} | "
            f"coach {coach.get('name') or 'unknown'}"
        )
        if players:
            lines.append(f"  XI: {', '.join(players)}")
    return lines


def _format_injuries(injuries: list[dict]) -> list[str]:
    lines = []
    for injury in injuries[:10]:
        player = injury.get("player") or {}
        team = injury.get("team") or {}
        fixture = injury.get("fixture") or {}
        league = injury.get("league") or {}
        lines.append(
            f"- {player.get('name') or 'Unknown player'} | {team.get('name') or 'Unknown team'} | "
            f"{injury.get('type') or 'Unavailable'} | {injury.get('reason') or 'reason unknown'} | "
            f"{league.get('name') or 'competition unknown'} | {(fixture.get('date') or '')[:10]}"
        )
    return lines


def _format_squad(players: list[dict]) -> list[str]:
    lines = []
    for player in players[:18]:
        lines.append(
            f"- {player.get('name') or 'Unknown player'} | {player.get('position') or 'Unknown position'} | "
            f"age {player.get('age') or 'unknown'}"
        )
    return lines


def _fetch_recent_fixtures(team_id: int, league_id: int | None, season_year: int, current_season: int) -> tuple[list[dict], int, list[str]]:
    diagnostics: list[str] = []
    attempts: list[dict] = []

    if league_id:
        attempts.append({"team": team_id, "league": league_id, "season": season_year, "last": 8})
        for fallback_season in _season_candidates(season_year, current_season):
            attempts.append({"team": team_id, "league": league_id, "season": fallback_season, "last": 8})

    for fallback_season in _season_candidates(season_year, current_season):
        attempts.append({"team": team_id, "season": fallback_season, "last": 8})

    today = date.today()
    windows = [
        (today - timedelta(days=180), today + timedelta(days=7)),
        (today - timedelta(days=365), today + timedelta(days=14)),
        (today - timedelta(days=730), today + timedelta(days=14)),
    ]
    for start, end in windows:
        params = {"team": team_id, "from": start.isoformat(), "to": end.isoformat()}
        if league_id:
            params["league"] = league_id
            params["season"] = season_year
        attempts.append(params)
        attempts.append({"team": team_id, "from": start.isoformat(), "to": end.isoformat()})

    attempts.append({"team": team_id, "last": 8})

    seen = set()
    for params in attempts:
        key = tuple(sorted(params.items()))
        if key in seen:
            continue
        seen.add(key)
        fixtures = _api_football_get("fixtures", params).get("response") or []
        diagnostics.append(f"fixtures {params} -> {len(fixtures)}")
        if fixtures:
            fixture_league = fixtures[0].get("league") or {}
            return fixtures[:8], int(fixture_league.get("season") or params.get("season") or season_year), diagnostics

    return [], season_year, diagnostics


def _fetch_next_fixtures(team_id: int, league_id: int | None, season_year: int) -> tuple[list[dict], list[str]]:
    diagnostics = []
    attempts = []
    if league_id:
        attempts.append({"team": team_id, "league": league_id, "season": season_year, "next": 4})
    attempts.append({"team": team_id, "next": 4})

    for params in attempts:
        fixtures = _api_football_get("fixtures", params).get("response") or []
        diagnostics.append(f"next fixtures {params} -> {len(fixtures)}")
        if fixtures:
            return fixtures[:4], diagnostics
    return [], diagnostics


def fetch_team_context_api_football(team_name: str) -> FootballTeamContext:
    clean_name = team_name.strip()
    if not clean_name:
        raise ValueError("team_name is required")

    search = _api_football_get("teams", {"search": clean_name})
    picked = _pick_api_football_team(search.get("response"))
    if not picked:
        raise LookupError(f"No football team found for '{clean_name}'")

    team, venue = picked
    team_id = team.get("id")
    resolved_name = team.get("name") or clean_name
    current_season = date.today().year
    league: dict = {}
    season: dict = {}
    league_id = None
    season_year = current_season
    diagnostics: list[str] = []

    try:
        league_items = _api_football_get("leagues", {"team": team_id}).get("response") or []
        diagnostics.append(f"leagues team={team_id} -> {len(league_items)}")
        picked_competition = _pick_latest_competition(league_items)
        if picked_competition:
            league, season = picked_competition
            league_id = league.get("id")
            season_year = season.get("year") or current_season
    except requests.RequestException:
        league_items = []

    fixtures: list[dict] = []
    next_fixtures: list[dict] = []
    if team_id:
        fixtures, season_year, fixture_diagnostics = _fetch_recent_fixtures(team_id, league_id, season_year, current_season)
        diagnostics.extend(fixture_diagnostics)
        if fixtures:
            fixture_league = fixtures[0].get("league") or {}
            league = fixture_league or league
            league_id = fixture_league.get("id") or league_id
            season_year = fixture_league.get("season") or season_year
        next_fixtures, next_diagnostics = _fetch_next_fixtures(team_id, league_id, season_year)
        diagnostics.extend(next_diagnostics)

    team_statistics: dict = {}
    if team_id and league_id:
        for stats_season in _season_candidates(season_year, current_season):
            try:
                candidate_stats = _api_football_get(
                    "teams/statistics",
                    {"team": team_id, "league": league_id, "season": stats_season},
                ).get("response") or {}
            except requests.RequestException:
                candidate_stats = {}
            diagnostics.append(f"team statistics league={league_id} season={stats_season} -> played {_stats_played_total(candidate_stats)}")
            if _stats_played_total(candidate_stats) > 0:
                team_statistics = candidate_stats
                season_year = stats_season
                break
            if candidate_stats and not team_statistics:
                team_statistics = candidate_stats

    squad: list[dict] = []
    try:
        squad_response = _api_football_get("players/squads", {"team": team_id}).get("response") or []
        if squad_response:
            squad = squad_response[0].get("players") or []
    except requests.RequestException:
        squad = []

    injuries: list[dict] = []
    try:
        injury_params = {"team": team_id, "season": season_year}
        if league_id:
            injury_params["league"] = league_id
        injuries = _api_football_get("injuries", injury_params).get("response") or []
        diagnostics.append(f"injuries {injury_params} -> {len(injuries)}")
    except requests.RequestException:
        injuries = []

    standings_lines: list[str] = []
    if league_id:
        try:
            standings_response = _api_football_get("standings", {"league": league_id, "season": season_year}).get("response") or []
            diagnostics.append(f"standings league={league_id} season={season_year} -> {len(standings_response)}")
            if standings_response:
                standings = ((standings_response[0].get("league") or {}).get("standings") or [])
                standings_lines = _format_standings(standings, team_id)
        except requests.RequestException:
            standings_lines = []

    lines = [
        f"Team: {resolved_name}",
        f"Country: {team.get('country') or 'Unknown'}",
        f"Founded: {team.get('founded') or 'Unknown'}",
        f"Venue: {venue.get('name') or 'Unknown'}",
        f"Venue capacity: {venue.get('capacity') or 'Unknown'}",
        f"Competition: {league.get('name') or 'Unknown'}",
        f"Season: {season_year}",
        f"Data provider: API-Football/API-Sports",
    ]

    team_stat_lines = _format_team_statistics(team_statistics)
    if team_stat_lines:
        lines.append("")
        lines.append("Season team statistics:")
        lines.extend(team_stat_lines)

    if standings_lines:
        lines.append("")
        lines.append("League standing:")
        lines.extend(standings_lines)

    if fixtures:
        lines.append("")
        lines.append("Recent matches:")
        lines.extend(f"- {_format_api_football_fixture(fixture, team_id)}" for fixture in fixtures)

        lines.append("")
        lines.append("Match statistics from recent fixtures:")
        added_stats = False
        for fixture in fixtures[:3]:
            fixture_id = (fixture.get("fixture") or {}).get("id")
            if not fixture_id:
                continue
            try:
                stats = _api_football_get("fixtures/statistics", {"fixture": fixture_id}).get("response") or []
            except requests.RequestException:
                stats = []
            stat_lines = _format_fixture_statistics(stats)
            if stat_lines:
                lines.append(f"Fixture {fixture_id}:")
                lines.extend(stat_lines)
                added_stats = True
        if not added_stats:
            lines.append("- No per-match statistics returned by provider for the recent fixtures.")

        lines.append("")
        lines.append("Recent lineups / formations:")
        added_lineups = False
        for fixture in fixtures[:3]:
            fixture_id = (fixture.get("fixture") or {}).get("id")
            if not fixture_id:
                continue
            try:
                lineups = _api_football_get("fixtures/lineups", {"fixture": fixture_id}).get("response") or []
            except requests.RequestException:
                lineups = []
            diagnostics.append(f"lineups fixture={fixture_id} -> {len(lineups)}")
            lineup_lines = _format_lineups(lineups)
            if lineup_lines:
                lines.append(f"Fixture {fixture_id}:")
                lines.extend(lineup_lines)
                added_lineups = True
        if not added_lineups:
            lines.append("- No lineups/formations returned by provider for the recent fixtures.")
    else:
        lines.append("")
        lines.append("Recent matches: none returned by provider after league/season and team-only fallbacks.")

    if next_fixtures:
        lines.append("")
        lines.append("Next fixtures:")
        lines.extend(f"- {_format_api_football_fixture(fixture, team_id)}" for fixture in next_fixtures)

    if injuries:
        lines.append("")
        lines.append("Injuries / suspensions / doubtful players:")
        lines.extend(_format_injuries(injuries))
    else:
        lines.append("")
        lines.append("Injuries / suspensions / doubtful players: none returned by provider for the selected team/season.")

    if squad:
        lines.append("")
        lines.append("Squad sample:")
        lines.extend(_format_squad(squad))

    lines.append("")
    lines.append("Provider diagnostics:")
    lines.extend(f"- {item}" for item in diagnostics[:20])

    observations = (
        "Automatic data loaded from API-Football/API-Sports. This includes recent fixtures, available match statistics, "
        "squad sample and injury/suspension availability where the provider has coverage. Add human tactical observations "
        "for pressing triggers, build-up patterns, transition behaviour, set pieces and individual matchups."
    )

    return FootballTeamContext(
        team_name=resolved_name,
        source="API-Football",
        stats="\n".join(lines),
        observations=observations,
    )


def fetch_team_context(team_name: str) -> FootballTeamContext:
    if _api_football_key():
        return fetch_team_context_api_football(team_name)

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
