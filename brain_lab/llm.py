import json
from typing import Any, Sequence

import requests

from brain_lab.agent_loop import AgentMessage, ModelResponse, ToolCall
from brain_lab.tools import list_tools

LLM_MODEL = "qwen3:14b"
LLM_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """You are Brain Lab, a personal notes assistant.

Use available tools whenever a request involves notes. If the user refers to "my notes" or similar without IDs, list notes first, then get or search them to build a complete answer.

Do not ask clarifying questions. Provide the best possible answer with the information and tools available.
"""


class LocalLLM:
    def respond(self, messages: Sequence[AgentMessage]) -> ModelResponse:
        payload = {
            "model": LLM_MODEL,
            "stream": False,
            "think": True,
            "messages": _build_messages(messages),
            "tools": [_tool_schema(t) for t in list_tools()],
        }
        resp = requests.post(LLM_URL, json=payload, timeout=120)
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
