from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from brain_lab.agent_loop import AgentRun, AgentStep


DEFAULT_RUN_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "runs.jsonl"
RESULT_SUMMARY_LIMIT = 500


def write_run_log(
    user_task: str,
    run: AgentRun | None = None,
    error: str | None = None,
    log_path: str | Path = DEFAULT_RUN_LOG_PATH,
    run_id: str | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    record = build_run_log_record(
        user_task=user_task,
        run=run,
        error=error,
        run_id=run_id,
        timestamp=timestamp,
    )
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, sort_keys=True))
        file.write("\n")

    return record


def build_run_log_record(
    user_task: str,
    run: AgentRun | None = None,
    error: str | None = None,
    run_id: str | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    errors = _errors_for_run(run)
    if error is not None:
        errors.append(error)

    return {
        "run_id": run_id or uuid4().hex,
        "timestamp": _format_timestamp(timestamp or datetime.now(UTC)),
        "user_task": user_task,
        "status": "error" if errors else "completed",
        "stopped_reason": run.stopped_reason if run is not None else None,
        "model_steps": _model_steps_for_run(run),
        "tool_calls": _tool_calls_for_run(run),
        "final_answer": run.final_answer if run is not None else None,
        "errors": errors,
    }


def list_run_logs(log_path: str | Path = DEFAULT_RUN_LOG_PATH) -> list[dict[str, Any]]:
    path = Path(log_path)
    if not path.exists():
        return []

    records = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))

    return records


def get_run_log(
    run_id: str,
    log_path: str | Path = DEFAULT_RUN_LOG_PATH,
) -> dict[str, Any] | None:
    for record in list_run_logs(log_path):
        if record.get("run_id") == run_id:
            return record

    return None


def _model_steps_for_run(run: AgentRun | None) -> list[dict[str, Any]]:
    if run is None:
        return []

    steps_by_number: dict[int, list[AgentStep]] = {}
    for step in run.steps:
        steps_by_number.setdefault(step.step_number, []).append(step)

    model_steps = [
        {
            "step_number": step_number,
            "kind": "tool_calls",
            "tool_calls": [_tool_call_record(step) for step in steps],
        }
        for step_number, steps in sorted(steps_by_number.items())
    ]

    if run.final_answer is not None:
        final_step_number = max(steps_by_number, default=0) + 1
        model_steps.append(
            {
                "step_number": final_step_number,
                "kind": "final_answer",
                "final_answer": run.final_answer,
            }
        )

    return model_steps


def _tool_calls_for_run(run: AgentRun | None) -> list[dict[str, Any]]:
    if run is None:
        return []

    return [_tool_call_record(step) for step in run.steps]


def _tool_call_record(step: AgentStep) -> dict[str, Any]:
    observation = step.observation
    return {
        "step_number": step.step_number,
        "name": step.tool_call.name,
        "arguments": _jsonable_mapping(step.tool_call.arguments),
        "ok": observation.ok,
        "result_summary": _summarize_result(observation.content),
        "error": observation.error,
    }


def _errors_for_run(run: AgentRun | None) -> list[str]:
    if run is None:
        return []

    errors = [
        step.observation.error
        for step in run.steps
        if step.observation.error is not None
    ]
    if run.stopped_reason == "max_steps":
        errors.append("Stopped after max steps without a final answer.")

    return errors


def _jsonable_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(dict(value), sort_keys=True, default=str))


def _summarize_result(content: str) -> str:
    if len(content) <= RESULT_SUMMARY_LIMIT:
        return content

    return f"{content[:RESULT_SUMMARY_LIMIT]}..."


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
