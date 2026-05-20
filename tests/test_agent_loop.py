import pytest

from brain_lab.agent_loop import FakeModel, ModelResponse, run_agent
from brain_lab.notes import list_notes


def test_agent_returns_final_answer_without_tools(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel([ModelResponse.final("No tools needed.")])

    result = run_agent("Say hello.", model, db_path=db_path)

    assert result.final_answer == "No tools needed."
    assert result.stopped_reason == "final_answer"
    assert result.steps == []
    assert model.calls[0][0].content == "Say hello."


def test_agent_runs_tool_call_and_returns_final_answer(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel(
        [
            ModelResponse.call_tool("create_note", {"title": "Agent loop", "body": "Tool calls stay explicit."}),
            ModelResponse.final("Created the note."),
        ]
    )

    result = run_agent("Create an agent loop note.", model, db_path=db_path)

    notes = list_notes(db_path=db_path)
    assert result.final_answer == "Created the note."
    assert result.stopped_reason == "final_answer"
    assert len(result.steps) == 1
    assert result.steps[0].observation.ok is True
    assert result.steps[0].observation.result == notes[0]
    assert notes[0].title == "Agent loop"
    assert "Agent loop" in model.calls[1][-1].content


def test_agent_enforces_max_steps(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel(
        [
            ModelResponse.call_tool("list_notes"),
            ModelResponse.call_tool("list_notes"),
        ]
    )
    events = []

    result = run_agent("Keep listing notes.", model, db_path=db_path, max_steps=2, progress=events.append)

    assert result.final_answer is None
    assert result.stopped_reason == "max_steps"
    assert len(result.steps) == 2
    assert len(model.calls) == 2
    assert events[-1].kind == "max_steps"
    assert events[-1].step_number == 2


def test_agent_reports_progress_events(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel(
        [
            ModelResponse.call_tool("create_note", {"title": "Progress"}),
            ModelResponse.final("Created the note."),
        ]
    )
    events = []

    run_agent("Create a note.", model, db_path=db_path, progress=events.append)

    assert [(event.kind, event.step_number) for event in events] == [
        ("model_request", 1),
        ("tool_call", 1),
        ("tool_result", 1),
        ("model_request", 2),
        ("final_answer", 2),
    ]
    assert events[1].tool_call.name == "create_note"
    assert events[2].observation.ok is True
    assert events[4].final_answer == "Created the note."


def test_agent_records_tool_errors_and_continues(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel(
        [
            ModelResponse.call_tool("missing_tool"),
            ModelResponse.final("I could not use that tool."),
        ]
    )

    result = run_agent("Use a missing tool.", model, db_path=db_path)

    assert result.final_answer == "I could not use that tool."
    assert len(result.steps) == 1
    assert result.steps[0].observation.ok is False
    assert result.steps[0].observation.error == "ValueError: Unknown tool: missing_tool"
    assert result.steps[0].observation.content.startswith("ERROR:")
    assert "Unknown tool" in model.calls[1][-1].content


def test_agent_rejects_empty_model_response(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel([ModelResponse()])

    with pytest.raises(ValueError, match="final answer or tool calls"):
        run_agent("Do something.", model, db_path=db_path)


def test_agent_requires_positive_max_steps(tmp_path):
    db_path = tmp_path / "brain.db"
    model = FakeModel([ModelResponse.final("Done.")])

    with pytest.raises(ValueError, match="max_steps"):
        run_agent("Do something.", model, db_path=db_path, max_steps=0)
