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
        if path == "standings":
            return {
                "response": [
                    {
                        "league": {
                            "standings": [
                                [
                                    {
                                        "rank": 2,
                                        "team": {"id": 1, "name": "Cruzeiro"},
                                        "points": 20,
                                        "form": "WWDLW",
                                        "all": {
                                            "played": 10,
                                            "win": 6,
                                            "draw": 2,
                                            "lose": 2,
                                            "goals": {"for": 18, "against": 9},
                                        },
                                    }
                                ]
                            ]
                        }
                    }
                ]
            }
        if path == "fixtures/lineups":
            return {
                "response": [
                    {
                        "team": {"name": "Cruzeiro"},
                        "formation": "4-2-3-1",
                        "coach": {"name": "Coach One"},
                        "startXI": [{"player": {"name": "Starter One", "pos": "G"}}],
                    }
                ]
            }
        raise AssertionError(path)

    monkeypatch.setattr(football_analysis, "_api_football_get", fake_api_get)

    context = fetch_team_context("Cruzeiro")

    assert context.source == "API-Football"
    assert "Competition: Brazilian Serie A" in context.stats
    assert "Season team statistics" in context.stats
    assert "League standing" in context.stats
    assert "Record: played 10, wins 6, draws 2, losses 2" in context.stats
    assert "Recent matches" in context.stats
    assert "Ball Possession: 57%" in context.stats
    assert "formation 4-2-3-1" in context.stats
    assert "Player Injured" in context.stats
    assert "Cássio" in context.stats
    assert "Provider diagnostics" in context.stats
    assert any(path == "injuries" for path, _params in calls)


def test_fetch_team_context_falls_back_to_team_only_fixtures(monkeypatch):
    from Api.services import football_analysis

    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")

    def fake_api_get(path, params=None):
        params = params or {}
        if path == "teams":
            return {
                "response": [
                    {
                        "team": {"id": 1, "name": "FC Porto", "country": "Portugal", "founded": 1893},
                        "venue": {"name": "Estadio do Dragao", "capacity": 50399},
                    }
                ]
            }
        if path == "leagues":
            return {
                "response": [
                    {
                        "league": {"id": 94, "name": "Primeira Liga", "type": "League"},
                        "seasons": [{"year": 2025, "current": True}],
                    }
                ]
            }
        if path == "fixtures" and params.get("last") and params.get("league"):
            return {"response": []}
        if path == "fixtures" and params.get("last") and not params.get("league"):
            return {
                "response": [
                    {
                        "fixture": {"id": 20, "date": "2026-05-18T20:00:00Z", "status": {"short": "FT"}, "venue": {"name": "Dragao"}},
                        "league": {"id": 94, "name": "Primeira Liga", "season": 2025},
                        "teams": {"home": {"id": 1, "name": "FC Porto"}, "away": {"id": 2, "name": "Benfica"}},
                        "goals": {"home": 2, "away": 0},
                    }
                ]
            }
        if path == "fixtures" and params.get("next"):
            return {"response": []}
        if path == "teams/statistics":
            return {
                "response": {
                    "fixtures": {"played": {"total": 2}, "wins": {"total": 2}, "draws": {"total": 0}, "loses": {"total": 0}},
                    "goals": {
                        "for": {"total": {"total": 4}, "average": {"total": "2.0"}},
                        "against": {"total": {"total": 0}, "average": {"total": "0.0"}},
                    },
                    "clean_sheet": {"total": 2},
                    "failed_to_score": {"total": 0},
                }
            }
        if path == "fixtures/statistics":
            return {"response": []}
        if path == "fixtures/lineups":
            return {"response": []}
        if path == "players/squads":
            return {"response": []}
        if path == "injuries":
            return {"response": []}
        if path == "standings":
            return {"response": []}
        raise AssertionError((path, params))

    monkeypatch.setattr(football_analysis, "_api_football_get", fake_api_get)

    context = fetch_team_context("FC Porto")

    assert "FC Porto 2-0 Benfica" in context.stats
    assert "Record: played 2, wins 2, draws 0, losses 0" in context.stats


def test_fetch_team_context_uses_football_data_matches_when_api_football_fixtures_empty(monkeypatch):
    from Api.services import football_analysis

    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")
    monkeypatch.setenv("FOOTBALL_DATA_API_KEY", "fd-key")

    def fake_api_get(path, params=None):
        params = params or {}
        if path == "teams":
            return {
                "response": [
                    {
                        "team": {"id": 211, "name": "Benfica", "country": "Portugal", "founded": 1904},
                        "venue": {"name": "Estadio da Luz", "capacity": 65647},
                    }
                ]
            }
        if path == "leagues":
            return {
                "response": [
                    {
                        "league": {"id": 94, "name": "Primeira Liga", "type": "League"},
                        "seasons": [{"year": 2024, "current": True}],
                    }
                ]
            }
        if path == "fixtures":
            return {"response": []}
        if path == "teams/statistics":
            return {
                "response": {
                    "fixtures": {"played": {"total": 34}, "wins": {"total": 25}, "draws": {"total": 5}, "loses": {"total": 4}},
                    "goals": {
                        "for": {"total": {"total": 84}, "average": {"total": "2.5"}},
                        "against": {"total": {"total": 28}, "average": {"total": "0.8"}},
                    },
                    "clean_sheet": {"total": 15},
                    "failed_to_score": {"total": 2},
                }
            }
        if path == "players/squads":
            return {"response": []}
        if path == "injuries":
            return {"response": []}
        if path == "standings":
            return {"response": []}
        raise AssertionError((path, params))

    def fake_football_data_get(path, params=None):
        if path == "teams":
            return {"teams": []}
        if path == "competitions/PPL/teams":
            return {"teams": [{"id": 1903, "name": "SL Benfica", "shortName": "Benfica", "tla": "BEN"}]}
        if path.startswith("competitions/"):
            return {"teams": []}
        if path == "teams/1903/matches":
            return {
                "matches": [
                    {
                        "utcDate": "2026-05-01T20:00:00Z",
                        "status": "FINISHED",
                        "competition": {"name": "Primeira Liga"},
                        "homeTeam": {"name": "SL Benfica"},
                        "awayTeam": {"name": "FC Porto"},
                        "score": {"fullTime": {"home": 2, "away": 1}},
                    }
                ]
            }
        raise AssertionError((path, params))

    monkeypatch.setattr(football_analysis, "_api_football_get", fake_api_get)
    monkeypatch.setattr(football_analysis, "_football_data_get", fake_football_data_get)

    context = fetch_team_context("Benfica")

    assert "Recent matches from football-data.org" in context.stats
    assert "SL Benfica 2-1 FC Porto" in context.stats
    assert "football-data.org team matches -> 1" in context.stats


def test_fetch_team_context_accepts_slash_separated_team_names(monkeypatch):
    from Api.services import football_analysis

    monkeypatch.setenv("API_FOOTBALL_KEY", "test-key")

    team_searches = []

    def fake_api_get(path, params=None):
        params = params or {}
        if path == "teams":
            team_searches.append(params.get("search"))
            if params.get("search") == "Benfica":
                return {
                    "response": [
                        {
                            "team": {"id": 211, "name": "Benfica", "country": "Portugal", "founded": 1904},
                            "venue": {"name": "Estadio da Luz", "capacity": 65647},
                        }
                    ]
                }
            return {"response": []}
        if path == "leagues":
            return {
                "response": [
                    {
                        "league": {"id": 94, "name": "Primeira Liga", "type": "League"},
                        "seasons": [{"year": 2024, "current": True}],
                    }
                ]
            }
        if path == "fixtures":
            return {"response": []}
        if path == "teams/statistics":
            return {"response": {"fixtures": {"played": {"total": 0}}}}
        if path == "players/squads":
            return {"response": []}
        if path == "injuries":
            return {
                "response": [
                    {
                        "player": {"name": "Player A"},
                        "team": {"name": "Benfica"},
                        "fixture": {"date": "2024-01-01T00:00:00Z"},
                        "league": {"name": "Primeira Liga"},
                        "type": "Injury",
                        "reason": "Old",
                    },
                    {
                        "player": {"name": "Player A"},
                        "team": {"name": "Benfica"},
                        "fixture": {"date": "2024-02-01T00:00:00Z"},
                        "league": {"name": "Primeira Liga"},
                        "type": "Injury",
                        "reason": "New",
                    },
                ]
            }
        if path == "standings":
            return {"response": []}
        raise AssertionError((path, params))

    monkeypatch.setattr(football_analysis, "_api_football_get", fake_api_get)

    context = fetch_team_context("Benfica/Porto")

    assert team_searches[:2] == ["Benfica/Porto", "Benfica"]
    assert context.team_name == "Benfica"
    assert "Player A" in context.stats
    assert "New" in context.stats
    assert "Old" not in context.stats


def test_team_search_terms_strip_quotes_and_expand_aliases():
    from Api.services.football_analysis import _normalise_team_name, _team_search_terms

    terms = _team_search_terms("'Benfica/porto")

    assert "Benfica" in terms
    assert "SL Benfica" in terms
    assert "porto" in terms
    assert "FC Porto" in terms
    assert _normalise_team_name("Benfica") == "benfica"
    assert _normalise_team_name("FC Bayern München") == "bayern munchen"


def test_football_data_team_matching_does_not_accept_empty_or_wrong_names():
    from Api.services.football_analysis import _football_data_team_matches

    assert _football_data_team_matches("Benfica", {"name": "SL Benfica", "shortName": "Benfica", "tla": "BEN"})
    assert not _football_data_team_matches("Benfica", {"name": "FC Bayern München", "shortName": "Bayern", "tla": "FCB"})
    assert not _football_data_team_matches("Benfica", {"name": None, "shortName": None, "tla": None})


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
