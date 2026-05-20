from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable, Literal, Protocol, Self

from pydantic import BaseModel

from brain_lab.db import DEFAULT_DB_PATH
from brain_lab.tools import run_tool


MessageRole = Literal["user", "assistant", "tool"]
StopReason = Literal["final_answer", "max_steps"]
ProgressKind = Literal[
    "model_request",
    "thinking",
    "tool_call",
    "tool_result",
    "final_answer",
    "max_steps",
]


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentMessage:
    role: MessageRole
    content: str = ""
    tool_calls: Sequence[ToolCall] = field(default_factory=tuple)


@dataclass(frozen=True)
class ModelResponse:
    final_answer: str | None = None
    tool_calls: Sequence[ToolCall] = field(default_factory=tuple)
    thinking: str | None = None

    @classmethod
    def final(cls, answer: str) -> Self:
        return cls(final_answer=answer)

    @classmethod
    def call_tool(cls, name: str, arguments: Mapping[str, Any] | None = None) -> Self:
        return cls(tool_calls=(ToolCall(name=name, arguments=arguments or {}),))


class Model(Protocol):
    def respond(self, messages: Sequence[AgentMessage]) -> ModelResponse:
        pass


class FakeModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[list[AgentMessage]] = []

    def respond(self, messages: Sequence[AgentMessage]) -> ModelResponse:
        self.calls.append(list(messages))

        if not self._responses:
            raise RuntimeError("FakeModel has no responses left.")

        return self._responses.pop(0)


@dataclass(frozen=True)
class ToolObservation:
    tool_name: str
    arguments: Mapping[str, Any]
    content: str
    result: Any | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class AgentStep:
    step_number: int
    tool_call: ToolCall
    observation: ToolObservation


@dataclass(frozen=True)
class AgentRun:
    final_answer: str | None
    stopped_reason: StopReason
    messages: list[AgentMessage]
    steps: list[AgentStep]


@dataclass(frozen=True)
class AgentProgress:
    kind: ProgressKind
    step_number: int
    tool_call: ToolCall | None = None
    observation: ToolObservation | None = None
    final_answer: str | None = None
    thinking: str | None = None


ProgressCallback = Callable[[AgentProgress], None]


def run_agent(
    prompt: str,
    model: Model,
    db_path: str | Path = DEFAULT_DB_PATH,
    max_steps: int = 10,
    progress: ProgressCallback | None = None,
) -> AgentRun:
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1.")

    messages = [AgentMessage(role="user", content=prompt)]
    steps: list[AgentStep] = []

    for step_number in range(1, max_steps + 1):
        _report_progress(progress, AgentProgress(kind="model_request", step_number=step_number))
        response = model.respond(tuple(messages))

        if response.thinking:
            _report_progress(
                progress,
                AgentProgress(kind="thinking", step_number=step_number, thinking=response.thinking),
            )

        if response.final_answer is not None:
            messages.append(AgentMessage(role="assistant", content=response.final_answer))
            _report_progress(
                progress,
                AgentProgress(kind="final_answer", step_number=step_number, final_answer=response.final_answer),
            )
            return AgentRun(
                final_answer=response.final_answer,
                stopped_reason="final_answer",
                messages=messages,
                steps=steps,
            )

        if not response.tool_calls:
            raise ValueError("Model response must include a final answer or tool calls.")

        normalized_calls = [
            ToolCall(name=tc.name, arguments=dict(tc.arguments))
            for tc in response.tool_calls
        ]
        messages.append(
            AgentMessage(role="assistant", content="", tool_calls=tuple(normalized_calls))
        )

        for tool_call in normalized_calls:
            _report_progress(
                progress,
                AgentProgress(kind="tool_call", step_number=step_number, tool_call=tool_call),
            )
            observation = _run_tool_call(tool_call, db_path)
            steps.append(AgentStep(step_number=step_number, tool_call=tool_call, observation=observation))
            _report_progress(
                progress,
                AgentProgress(kind="tool_result", step_number=step_number, tool_call=tool_call, observation=observation),
            )
            messages.append(AgentMessage(role="tool", content=observation.content))

    _report_progress(progress, AgentProgress(kind="max_steps", step_number=max_steps))
    return AgentRun(final_answer=None, stopped_reason="max_steps", messages=messages, steps=steps)


def _report_progress(progress: ProgressCallback | None, event: AgentProgress) -> None:
    if progress is not None:
        progress(event)


def _run_tool_call(tool_call: ToolCall, db_path: str | Path) -> ToolObservation:
    arguments = dict(tool_call.arguments)
    try:
        result = run_tool(tool_call.name, arguments, db_path=db_path)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        return ToolObservation(
            tool_name=tool_call.name,
            arguments=arguments,
            content=f"ERROR: {error}",
            error=error,
        )
    return ToolObservation(
        tool_name=tool_call.name,
        arguments=arguments,
        content=_format_content(result),
        result=result,
    )


def _format_content(value: Any) -> str:
    return json.dumps(_to_jsonable(value), sort_keys=True)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_jsonable(item) for item in value]
    return value
