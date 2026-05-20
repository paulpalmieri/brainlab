import brain_lab.llm as llm
from brain_lab.agent_loop import AgentMessage, ToolCall
from brain_lab.llm import (
    LLM_MODEL,
    LLM_URL,
    LocalLLM,
    SYSTEM_PROMPT,
)


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_local_llm_sends_correct_request(monkeypatch):
    captured = {}

    def mock_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse({"message": {"role": "assistant", "content": "There are no notes.", "thinking": None, "tool_calls": None}})

    monkeypatch.setattr(llm.requests, "post", mock_post)
    model = LocalLLM()

    response = model.respond([AgentMessage(role="user", content="List notes.")])

    assert response.final_answer == "There are no notes."
    assert captured["url"] == LLM_URL
    payload = captured["payload"]
    assert payload["model"] == LLM_MODEL
    assert payload["stream"] is False
    assert payload["think"] is True
    assert payload["messages"][0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert payload["messages"][1] == {"role": "user", "content": "List notes."}
    assert any(t["function"]["name"] == "create_note" for t in payload["tools"])


def test_local_llm_parses_tool_calls(monkeypatch):
    def mock_post(url, json=None, timeout=None):
        return FakeResponse({
            "message": {
                "role": "assistant",
                "content": "",
                "thinking": "Let me list the notes.",
                "tool_calls": [{"function": {"name": "list_notes", "arguments": {}}}],
            }
        })

    monkeypatch.setattr(llm.requests, "post", mock_post)
    model = LocalLLM()

    response = model.respond([AgentMessage(role="user", content="List notes.")])

    assert response.final_answer is None
    assert response.tool_calls == (ToolCall(name="list_notes", arguments={}),)

    assert response.thinking == "Let me list the notes."


def test_local_llm_extracts_thinking(monkeypatch):
    def mock_post(url, json=None, timeout=None):
        return FakeResponse({
            "message": {
                "role": "assistant",
                "content": "The answer is 3.",
                "thinking": "s, t, r... there are 3 r's.",
                "tool_calls": None,
            }
        })

    monkeypatch.setattr(llm.requests, "post", mock_post)
    model = LocalLLM()

    response = model.respond([AgentMessage(role="user", content="How many r's in strawberry?")])

    assert response.final_answer == "The answer is 3."
    assert response.thinking == "s, t, r... there are 3 r's."


def test_local_llm_sends_tool_result_messages(monkeypatch):
    captured = {}

    def mock_post(url, json=None, timeout=None):
        captured["payload"] = json
        return FakeResponse({"message": {"role": "assistant", "content": "Done.", "thinking": None, "tool_calls": None}})

    monkeypatch.setattr(llm.requests, "post", mock_post)
    model = LocalLLM()

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


def test_local_llm_raises_on_http_error(monkeypatch):
    import pytest

    def mock_post(url, json=None, timeout=None):
        class FailResponse:
            def raise_for_status(self):
                raise Exception("Connection refused")
            def json(self):
                return {}
        return FailResponse()

    monkeypatch.setattr(llm.requests, "post", mock_post)
    model = LocalLLM()

    with pytest.raises(Exception, match="Connection refused"):
        model.respond([AgentMessage(role="user", content="Hello.")])
