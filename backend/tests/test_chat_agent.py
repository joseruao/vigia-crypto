import sys
from types import SimpleNamespace

from fastapi.testclient import TestClient

from Api.main import app


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeChoice:
    def __init__(self, message):
        self.message = message


class _FakeResponse:
    def __init__(self, message):
        self.choices = [_FakeChoice(message)]


def test_chat_stream_uses_openai_tool_calling_fallback(monkeypatch):
    from Api import main

    calls = []

    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_listing_predictions", arguments="{}"),
    )

    class _Completions:
        def create(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return _FakeResponse(_FakeMessage(tool_calls=[tool_call]))
            return _FakeResponse(_FakeMessage(content="Resposta final com listings."))

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_Completions()))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda api_key: fake_client))

    async def fake_execute_tool(name, arguments=None):
        return {"ok": True, "answer": "LISTING TOOL ANSWER"}

    monkeypatch.setattr(main, "execute_tool", fake_execute_tool)

    client = TestClient(app)
    response = client.post("/chat/stream", json={"prompt": "faz uma leitura geral do mercado crypto", "history": []})

    assert response.status_code == 200
    assert "Resposta final com listings" in response.text
    assert calls[0]["tools"]
    assert calls[0]["model"] == "gpt-4o-mini"


def test_chat_stream_keeps_top100_fast_path_without_openai(monkeypatch):
    from Api import main

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        main,
        "answer_top100_buy_watchlist",
        lambda log=None, prompt="": {"ok": True, "answer": "FAST TOP100", "count": 1, "items": []},
    )

    client = TestClient(app)
    response = client.post("/chat/stream", json={"prompt": "quais do top100 tem menos risco?", "history": []})

    assert response.status_code == 200
    assert "FAST TOP100" in response.text


def test_chat_stream_routes_listing_question_to_internal_tool(monkeypatch):
    from Api import main

    async def fake_execute_tool(name, arguments=None):
        assert name == "get_listing_predictions"
        return {"ok": True, "answer": "FAST LISTINGS"}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main, "execute_tool", fake_execute_tool)

    client = TestClient(app)
    response = client.post(
        "/chat/stream",
        json={"prompt": "Que tokens as exchanges estao a acumular que ainda nao foram listados?", "history": []},
    )

    assert response.status_code == 200
    assert "FAST LISTINGS" in response.text


def test_chat_stream_routes_recent_holdings_question_to_internal_tool(monkeypatch):
    from Api import main

    async def fake_execute_tool(name, arguments=None):
        assert name == "get_recent_holdings"
        return {"ok": True, "answer": "FAST HOLDINGS"}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main, "execute_tool", fake_execute_tool)

    client = TestClient(app)
    response = client.post("/chat/stream", json={"prompt": "mostra holdings recentes", "history": []})

    assert response.status_code == 200
    assert "FAST HOLDINGS" in response.text


def test_chat_stream_routes_whale_suggestion_to_smart_money_before_top100(monkeypatch):
    from Api import main

    async def fake_execute_tool(name, arguments=None):
        assert name == "get_smart_money"
        assert arguments == {"lang": "pt"}
        return {"ok": True, "answer": "FAST SMART MONEY"}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(main, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(
        main,
        "answer_top100_buy_watchlist",
        lambda log=None, prompt="": {"ok": True, "answer": "WRONG TOP100", "count": 1, "items": []},
    )

    client = TestClient(app)
    response = client.post("/chat/stream", json={"prompt": "O que as whales compraram hoje?", "history": []})

    assert response.status_code == 200
    assert "FAST SMART MONEY" in response.text
    assert "WRONG TOP100" not in response.text
