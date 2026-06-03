from fastapi.testclient import TestClient

from Api.main import app
from Api.services.football_analysis import FootballAnalysisReport, FootballAnalyzeResponse


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
