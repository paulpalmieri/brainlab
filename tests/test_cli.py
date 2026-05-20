from datetime import UTC, datetime
import json

import pytest
from typer.testing import CliRunner

from brain_lab import cli
from brain_lab.agent_loop import FakeModel, ModelResponse
from brain_lab.llm import LLM_MODEL, LLM_URL
from brain_lab.run_logs import write_run_log


@pytest.fixture
def run_log_path(tmp_path, monkeypatch):
    path = tmp_path / "runs.jsonl"
    monkeypatch.setattr(cli, "DEFAULT_RUN_LOG_PATH", path)
    return path


def test_ask_command_runs_agent_and_prints_answer(monkeypatch, run_log_path):
    runner = CliRunner()

    monkeypatch.setattr(
        cli,
        "LocalLLM",
        lambda: FakeModel([ModelResponse.final("Agent answer.")]),
    )

    result = runner.invoke(cli.app, ["ask", "Answer from notes."])

    assert result.exit_code == 0
    assert result.stdout == "Agent answer.\n"
    assert "Run logged:" in result.stderr

    records = _read_jsonl(run_log_path)
    assert len(records) == 1
    assert records[0]["user_task"] == "Answer from notes."
    assert records[0]["final_answer"] == "Agent answer."


def test_ask_command_uses_local_llm_defaults(monkeypatch, run_log_path):
    runner = CliRunner()
    captured = {}

    def fake_local_llm():
        captured["created"] = True
        return FakeModel([ModelResponse.final("Custom model answer.")])

    monkeypatch.setattr(cli, "LocalLLM", fake_local_llm)

    result = runner.invoke(cli.app, ["ask", "hello"])

    assert result.exit_code == 0
    assert captured["created"] is True
    assert LLM_MODEL in result.stderr
    assert LLM_URL in result.stderr


def test_ask_command_reports_errors(monkeypatch, run_log_path):
    runner = CliRunner()

    def fake_local_llm():
        raise RuntimeError("Connection refused.")

    monkeypatch.setattr(cli, "LocalLLM", fake_local_llm)

    result = runner.invoke(cli.app, ["ask", "Answer from notes."])

    assert result.exit_code == 1
    assert "Connection refused." in result.stderr

    records = _read_jsonl(run_log_path)
    assert len(records) == 1
    assert records[0]["user_task"] == "Answer from notes."
    assert records[0]["status"] == "error"
    assert records[0]["errors"] == ["RuntimeError: Connection refused."]


def test_runs_list_shows_logged_runs(run_log_path):
    runner = CliRunner()
    write_run_log(
        user_task="List notes with sqlite in them.",
        run_id="run_123",
        timestamp=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
        log_path=run_log_path,
    )

    result = runner.invoke(cli.app, ["runs", "list"])

    assert result.exit_code == 0
    assert "2026-05-19T12:00:00Z | run_123 | completed" in result.output
    assert "List notes with sqlite in them." in result.output


def test_runs_show_prints_selected_run(run_log_path):
    runner = CliRunner()
    write_run_log(
        user_task="First task.",
        run_id="run_first",
        timestamp=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
        log_path=run_log_path,
    )
    write_run_log(
        user_task="Second task.",
        run_id="run_second",
        timestamp=datetime(2026, 5, 19, 12, 1, tzinfo=UTC),
        log_path=run_log_path,
    )

    result = runner.invoke(cli.app, ["runs", "show", "run_second"])

    assert result.exit_code == 0
    record = json.loads(result.output)
    assert record["run_id"] == "run_second"
    assert record["user_task"] == "Second task."


def test_runs_show_reports_missing_run(run_log_path):
    runner = CliRunner()

    result = runner.invoke(cli.app, ["runs", "show", "missing"])

    assert result.exit_code == 1
    assert "Run not found." in result.stderr


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
