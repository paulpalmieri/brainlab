import json
import os
from dataclasses import dataclass
from typing import Any, Sequence

import requests

from brain_lab.agent_loop import AgentMessage, ModelResponse, ToolCall
from brain_lab.tools import list_tools

DEFAULT_OLLAMA_BASE_URL = "http://192.168.1.43:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:14b"
OLLAMA_MODEL = os.environ.get("BRAIN_LAB_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def ollama_chat_url(value: str | None = None) -> str:
    raw_url = value or os.environ.get("BRAIN_LAB_OLLAMA_URL") or DEFAULT_OLLAMA_BASE_URL
    url = raw_url.rstrip("/")

    if url.endswith("/api/chat"):
        return url
    if url.endswith("/api"):
        return f"{url}/chat"
    return f"{url}/api/chat"


OLLAMA_URL = ollama_chat_url()

SYSTEM_PROMPT = """You are Brain Lab, a personal notes assistant.

Use available tools whenever a request involves notes. If the user refers to "my notes" or similar without IDs, list notes first, then get or search them to build a complete answer.

Do not ask clarifying questions. Provide the best possible answer with the information and tools available.
"""


@dataclass
class OllamaModel:
    url: str = ""
    model: str = OLLAMA_MODEL

    def __post_init__(self) -> None:
        self.url = ollama_chat_url(self.url)

    def respond(self, messages: Sequence[AgentMessage]) -> ModelResponse:
        payload = {
            "model": self.model,
            "stream": False,
            "think": True,
            "messages": _build_messages(messages),
            "tools": [_tool_schema(t) for t in list_tools()],
        }
        resp = requests.post(self.url, json=payload, timeout=120)
        resp.raise_for_status()
        msg = resp.json()["message"]

        thinking = msg.get("thinking") or None
        content = (msg.get("content") or "").strip()
        tool_calls_raw = msg.get("tool_calls") or []

        if tool_calls_raw:
            return ModelResponse(
                tool_calls=tuple(
                    ToolCall(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    )
                    for tc in tool_calls_raw
                ),
                thinking=thinking,
            )

        return ModelResponse(final_answer=content, thinking=thinking)


def _build_messages(messages: Sequence[AgentMessage]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in messages:
        if msg.role == "user":
            result.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant" and msg.tool_calls:
            result.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": tc.name, "arguments": dict(tc.arguments)}}
                    for tc in msg.tool_calls
                ],
            })
        elif msg.role == "assistant":
            result.append({"role": "assistant", "content": msg.content})
        elif msg.role == "tool":
            result.append({"role": "tool", "content": msg.content})
    return result


def _tool_schema(tool: Any) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }
