from datetime import UTC, datetime

from brain_lab.agent_loop import AgentRun, AgentStep, ToolCall, ToolObservation
from brain_lab.run_logs import get_run_log, list_run_logs, write_run_log


def test_write_run_log_records_agent_run(tmp_path):
    log_path = tmp_path / "runs.jsonl"
    run = AgentRun(
        final_answer="Found one note.",
        stopped_reason="final_answer",
        messages=[],
        steps=[
            AgentStep(
                step_number=1,
                tool_call=ToolCall(name="search_notes", arguments={"query": "sqlite"}),
                observation=ToolObservation(
                    tool_name="search_notes",
                    arguments={"query": "sqlite"},
                    content='[{"id": "note_1", "title": "SQLite"}]',
                    result=[],
                ),
            )
        ],
    )

    record = write_run_log(
        user_task="Search for sqlite notes.",
        run=run,
        log_path=log_path,
        run_id="run_test",
        timestamp=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
    )

    assert record["run_id"] == "run_test"
    assert record["timestamp"] == "2026-05-19T12:00:00Z"
    assert record["user_task"] == "Search for sqlite notes."
    assert record["status"] == "completed"
    assert record["final_answer"] == "Found one note."
    assert record["errors"] == []
    assert record["model_steps"][0]["step_number"] == 1
    assert record["model_steps"][0]["kind"] == "tool_calls"
    assert record["model_steps"][1]["kind"] == "final_answer"
    assert record["tool_calls"] == [
        {
            "step_number": 1,
            "name": "search_notes",
            "arguments": {"query": "sqlite"},
            "ok": True,
            "result_summary": '[{"id": "note_1", "title": "SQLite"}]',
            "error": None,
        }
    ]
    assert list_run_logs(log_path) == [record]
    assert get_run_log("run_test", log_path) == record


def test_write_run_log_records_tool_errors(tmp_path):
    log_path = tmp_path / "runs.jsonl"
    run = AgentRun(
        final_answer="I could not use that tool.",
        stopped_reason="final_answer",
        messages=[],
        steps=[
            AgentStep(
                step_number=1,
                tool_call=ToolCall(name="missing_tool", arguments={}),
                observation=ToolObservation(
                    tool_name="missing_tool",
                    arguments={},
                    content="ERROR: ValueError: Unknown tool: missing_tool",
                    error="ValueError: Unknown tool: missing_tool",
                ),
            )
        ],
    )

    record = write_run_log(
        user_task="Use a missing tool.",
        run=run,
        log_path=log_path,
        run_id="run_error",
    )

    assert record["status"] == "error"
    assert record["errors"] == ["ValueError: Unknown tool: missing_tool"]
    assert record["tool_calls"][0]["ok"] is False
    assert record["tool_calls"][0]["error"] == "ValueError: Unknown tool: missing_tool"
