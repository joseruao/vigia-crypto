from fastapi.testclient import TestClient

from Api.main import app
from Api.services.football_analysis import (
    FootballAnalysisReport,
    FootballAnalyzeResponse,
    fetch_team_context_api_football,
    fetch_team_context,
)


def test_football_analyze_endpoint_returns_structured_report(monkeypatch):
    from Api.routes import football

    def fake_generate(payload):
        return FootballAnalyzeResponse(
            team_name=payload.team_name,
            report=FootballAnalysisReport(
                executive_summary="Compact summary.",
                tactical_strengths=["Strong wide rotations"],
                tactical_weaknesses=["Space behind full backs"],
                key_players_to_watch=["Right winger"],
                recommended_match_strategy="Force play inside and attack transition space.",
                pressing_recommendations=["Press backward passes"],
                set_piece_considerations=["Protect back post"],
                risk_assessment="Main risk is conceding from fast switches.",
            ),
        )

    monkeypatch.setattr(football, "generate_opponent_report", fake_generate)

    client = TestClient(app)
    response = client.post(
        "/api/football/analyze",
        json={
            "team_name": "FC Example",
            "stats": "PPDA 8.9",
            "observations": "Full backs push high.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == "FC Example"
    assert data["report"]["executive_summary"] == "Compact summary."
    assert data["report"]["tactical_strengths"] == ["Strong wide rotations"]


def test_fetch_team_context_builds_stats_from_public_data(monkeypatch):
    from Api.services import football_analysis

    responses = {
        "searchteams.php": {
            "teams": [
                {
                    "idTeam": "123",
                    "strTeam": "Cruzeiro",
                    "strSport": "Soccer",
                    "strLeague": "Campeonato Brasileiro Serie A",
                    "strCountry": "Brazil",
                    "strStadium": "Mineirao",
                    "intFormedYear": "1921",
                    "strDescriptionEN": "Cruzeiro is a Brazilian football club.",
                }
            ]
        },
        "eventslast.php": {
            "results": [
                {
                    "dateEvent": "2026-05-01",
                    "strLeague": "Serie A",
                    "strHomeTeam": "Cruzeiro",
                    "strAwayTeam": "Atletico",
                    "intHomeScore": "2",
                    "intAwayScore": "1",
                }
            ]
        },
        "eventsnext.php": {"events": []},
        "lookup_all_players.php": {
            "player": [
                {
                    "strPlayer": "Player One",
                    "strPosition": "Midfielder",
                    "strNationality": "Brazil",
                }
            ]
        },
    }

    def fake_get(path):
        for key, payload in responses.items():
            if path.startswith(key):
                return payload
        raise AssertionError(path)

    monkeypatch.setattr(football_analysis, "_sportsdb_get", fake_get)

    context = fetch_team_context("Cruzeiro")

    assert context.team_name == "Cruzeiro"
    assert context.source == "TheSportsDB"
    assert "Campeonato Brasileiro Serie A" in context.stats
    assert "Cruzeiro 2-1 Atletico" in context.stats
    assert "Player One" in context.stats


def test_fetch_team_context_uses_api_football_when_key_exists(monkeypatch):
    from Api.services import football_analysis

    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")

    calls = []

    def fake_api_get(path, params=None):
        calls.append((path, params or {}))
        if path == "teams":
            return {
                "response": [
                    {
                        "team": {
                            "id": 1,
                            "name": "Cruzeiro",
                            "country": "Brazil",
                            "founded": 1921,
                        },
                        "venue": {"name": "Mineirao", "capacity": 62547},
                    }
                ]
            }
        if path == "leagues":
            return {
                "response": [
                    {
                        "league": {"id": 71, "name": "Brazilian Serie A"},
                        "seasons": [{"year": 2026, "current": True}],
                    }
                ]
            }
        if path == "fixtures" and (params or {}).get("last"):
            assert (params or {}).get("league") == 71
            assert (params or {}).get("season") == 2026
            return {
                "response": [
                    {
                        "fixture": {"id": 10, "date": "2026-05-31T20:00:00Z", "status": {"short": "FT"}, "venue": {"name": "Mineirao"}},
                        "league": {"name": "Brazilian Serie A"},
                        "teams": {"home": {"id": 1, "name": "Cruzeiro"}, "away": {"id": 2, "name": "Fluminense"}},
                        "goals": {"home": 1, "away": 1},
                    }
                ]
            }
        if path == "fixtures" and (params or {}).get("next"):
            return {"response": []}
        if path == "teams/statistics":
            assert (params or {}).get("league") == 71
            assert (params or {}).get("season") == 2026
            return {
                "response": {
                    "fixtures": {
                        "played": {"total": 10},
                        "wins": {"total": 6},
                        "draws": {"total": 2},
                        "loses": {"total": 2},
                    },
                    "goals": {
                        "for": {"total": {"total": 18}, "average": {"total": "1.8"}},
                        "against": {"total": {"total": 9}, "average": {"total": "0.9"}},
                    },
                    "clean_sheet": {"total": 4},
                    "failed_to_score": {"total": 1},
                    "biggest": {"streak": {"wins": 3, "draws": 1, "loses": 1}},
                    "cards": {"yellow": {}, "red": {}},
                }
            }
        if path == "fixtures/statistics":
            return {
                "response": [
                    {
                        "team": {"name": "Cruzeiro"},
                        "statistics": [
                            {"type": "Ball Possession", "value": "57%"},
                            {"type": "Total Shots", "value": 14},
                        ],
                    }
                ]
            }
        if path == "players/squads":
            return {"response": [{"players": [{"name": "Cássio", "position": "Goalkeeper", "age": 39}]}]}
        if path == "injuries":
            return {
                "response": [
                    {
                        "player": {"name": "Player Injured"},
                        "team": {"name": "Cruzeiro"},
                        "fixture": {"date": "2026-06-01T20:00:00Z"},
                        "league": {"name": "Brazilian Serie A"},
                        "type": "Injury",
                        "reason": "Muscle injury",
                    }
                ]
            }
        raise AssertionError(path)

    monkeypatch.setattr(football_analysis, "_api_football_get", fake_api_get)

    context = fetch_team_context("Cruzeiro")

    assert context.source == "API-Football"
    assert "Competition: Brazilian Serie A" in context.stats
    assert "Season team statistics" in context.stats
    assert "Record: played 10, wins 6, draws 2, losses 2" in context.stats
    assert "Last 5 matches" in context.stats
    assert "Ball Possession: 57%" in context.stats
    assert "Player Injured" in context.stats
    assert "Cássio" in context.stats
    assert any(path == "injuries" for path, _params in calls)


def test_fetch_team_context_api_football_requires_key(monkeypatch):
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.delenv("APISPORTS_KEY", raising=False)

    try:
        fetch_team_context_api_football("Cruzeiro")
    except RuntimeError as exc:
        assert "API_FOOTBALL_KEY" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")


def test_football_team_context_endpoint_handles_missing_team(monkeypatch):
    from Api.routes import football

    def fake_fetch(team_name):
        raise LookupError("No football team found")

    monkeypatch.setattr(football, "fetch_team_context", fake_fetch)

    client = TestClient(app)
    response = client.get("/api/football/team-context?team_name=Missing")

    assert response.status_code == 404
