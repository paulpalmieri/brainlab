import brain_lab.provider_models as provider_models
from brain_lab.agent_loop import AgentMessage, ToolCall
from brain_lab.provider_models import (
    OLLAMA_MODEL,
    OLLAMA_URL,
    OllamaModel,
    SYSTEM_PROMPT,
    ollama_chat_url,
)


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_ollama_model_sends_correct_request(monkeypatch):
    captured = {}

    def mock_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse({"message": {"role": "assistant", "content": "There are no notes.", "thinking": None, "tool_calls": None}})

    monkeypatch.setattr(provider_models.requests, "post", mock_post)
    model = OllamaModel()

    response = model.respond([AgentMessage(role="user", content="List notes.")])

    assert response.final_answer == "There are no notes."
    assert captured["url"] == OLLAMA_URL
    payload = captured["payload"]
    assert payload["model"] == OLLAMA_MODEL
    assert payload["stream"] is False
    assert payload["think"] is True
    assert payload["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert payload["messages"][1] == {"role": "user", "content": "List notes."}
    assert any(t["function"]["name"] == "create_note" for t in payload["tools"])


def test_ollama_model_parses_tool_calls(monkeypatch):
    def mock_post(url, json=None, timeout=None):
        return FakeResponse({
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": "Let me list the notes.",
                "tool_calls": [{"function": {"name": "list_notes", "arguments": {}}}],
            }
        })

    monkeypatch.setattr(provider_models.requests, "post", mock_post)
    model = OllamaModel()

    response = model.respond([AgentMessage(role="user", content="List notes.")])

    assert response.final_answer is None
    assert response.tool_calls == (ToolCall(name="list_notes", arguments={}),)

    assert response.thinking == "Let me list the notes."


def test_ollama_model_extracts_thinking(monkeypatch):
    def mock_post(url, json=None, timeout=None):
        return FakeResponse({
            "message": {
                "role": "assistant",
                "content": "The answer is 3.",
                "thinking": "s, t, r... there are 3 r's.",
                "tool_calls": None,
            }
        })

    monkeypatch.setattr(provider_models.requests, "post", mock_post)
    model = OllamaModel()

    response = model.respond([AgentMessage(role="user", content="How many r's in strawberry?")])

    assert response.final_answer == "The answer is 3."
    assert response.thinking == "s, t, r... there are 3 r's."


def test_ollama_model_sends_tool_result_messages(monkeypatch):
    captured = {}

    def mock_post(url, json=None, timeout=None):
        captured["payload"] = json
        return FakeResponse({"message": {"role": "assistant", "content": "Done.", "thinking": None, "tool_calls": None}})

    monkeypatch.setattr(provider_models.requests, "post", mock_post)
    model = OllamaModel()

    messages = [
        AgentMessage(role="user", content="List notes."),
        AgentMessage(role="assistant", tool_calls=(ToolCall(name="list_notes", arguments={}),)),
        AgentMessage(role="tool", content="[]"),
    ]

    response = model.respond(messages)

    assert response.final_answer == "Done."
    msgs = captured["payload"]["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[2]["role"] == "assistant"
    assert msgs[2]["tool_calls"][0]["function"]["name"] == "list_notes"
    assert msgs[3]["role"] == "tool"
    assert msgs[3]["content"] == "[]"


def test_ollama_model_raises_on_http_error(monkeypatch):
    import pytest

    def mock_post(url, json=None, timeout=None):
        class FailResponse:
            def raise_for_status(self):
                raise Exception("Connection refused")
            def json(self):
                return {}
        return FailResponse()

    monkeypatch.setattr(provider_models.requests, "post", mock_post)
    model = OllamaModel()

    with pytest.raises(Exception, match="Connection refused"):
        model.respond([AgentMessage(role="user", content="Hello.")])


def test_ollama_model_custom_url_and_model(monkeypatch):
    captured = {}

    def mock_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["model"] = json["model"]
        return FakeResponse({"message": {"role": "assistant", "content": "ok", "thinking": None, "tool_calls": None}})

    monkeypatch.setattr(provider_models.requests, "post", mock_post)
    model = OllamaModel(url="http://localhost:11434/api/chat", model="llama3.2")

    model.respond([AgentMessage(role="user", content="hello")])

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["model"] == "llama3.2"


def test_ollama_chat_url_accepts_base_api_or_endpoint():
    assert ollama_chat_url("http://localhost:11434") == "http://localhost:11434/api/chat"
    assert ollama_chat_url("http://localhost:11434/api") == "http://localhost:11434/api/chat"
    assert ollama_chat_url("http://localhost:11434/api/chat") == "http://localhost:11434/api/chat"
