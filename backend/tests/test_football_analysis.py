from fastapi.testclient import TestClient

from Api.main import app
from Api.services.football_analysis import (
    FootballAnalysisReport,
    FootballAnalyzeResponse,
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


def test_football_team_context_endpoint_handles_missing_team(monkeypatch):
    from Api.routes import football

    def fake_fetch(team_name):
        raise LookupError("No football team found")

    monkeypatch.setattr(football, "fetch_team_context", fake_fetch)

    client = TestClient(app)
    response = client.get("/api/football/team-context?team_name=Missing")

    assert response.status_code == 404
