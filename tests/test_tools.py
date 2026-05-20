import pytest
from pydantic import ValidationError

from brain_lab.models import Note
from brain_lab.tools import TOOL_REGISTRY, list_tools, run_tool


def test_registry_contains_note_tools():
    tool_names = {tool.name for tool in list_tools()}

    assert tool_names == {
        "create_note",
        "list_notes",
        "get_note",
        "update_note",
        "delete_note",
        "search_notes",
    }
    assert set(TOOL_REGISTRY) == tool_names


def test_create_and_list_note_tools(tmp_path):
    db_path = tmp_path / "brain.db"

    created = run_tool(
        "create_note",
        {
            "title": "Tool layer",
            "body": "Wrap business logic.",
            "tags": ["tooling", "notes"],
        },
        db_path=db_path,
    )
    notes = run_tool("list_notes", db_path=db_path)

    assert isinstance(created, Note)
    assert created.title == "Tool layer"
    assert created.body == "Wrap business logic."
    assert created.tags == ["tooling", "notes"]
    assert notes == [created]


def test_get_note_tool_returns_note_or_none(tmp_path):
    db_path = tmp_path / "brain.db"
    created = run_tool("create_note", {"title": "Find me"}, db_path=db_path)

    found = run_tool("get_note", {"note_id": created.id}, db_path=db_path)
    missing = run_tool("get_note", {"note_id": "missing-note-id"}, db_path=db_path)

    assert found == created
    assert missing is None


def test_update_note_tool_changes_existing_note(tmp_path):
    db_path = tmp_path / "brain.db"
    created = run_tool(
        "create_note",
        {"title": "Draft", "body": "Old body", "tags": ["draft"]},
        db_path=db_path,
    )

    updated = run_tool(
        "update_note",
        {
            "note_id": created.id,
            "title": "Final",
            "tags": ["done"],
        },
        db_path=db_path,
    )

    assert updated is not None
    assert updated.id == created.id
    assert updated.title == "Final"
    assert updated.body == "Old body"
    assert updated.tags == ["done"]


def test_delete_note_tool_returns_bool(tmp_path):
    db_path = tmp_path / "brain.db"
    created = run_tool("create_note", {"title": "Temporary"}, db_path=db_path)

    deleted = run_tool("delete_note", {"note_id": created.id}, db_path=db_path)
    deleted_again = run_tool("delete_note", {"note_id": created.id}, db_path=db_path)

    assert deleted is True
    assert deleted_again is False


def test_search_notes_tool_matches_existing_notes(tmp_path):
    db_path = tmp_path / "brain.db"
    first = run_tool("create_note", {"title": "SQLite notes"}, db_path=db_path)
    run_tool("create_note", {"title": "Shopping list"}, db_path=db_path)

    matches = run_tool("search_notes", {"query": "sqlite"}, db_path=db_path)

    assert matches == [first]


def test_run_tool_validates_arguments(tmp_path):
    db_path = tmp_path / "brain.db"

    with pytest.raises(ValidationError):
        run_tool("create_note", {"body": "Missing title"}, db_path=db_path)

    with pytest.raises(ValidationError):
        run_tool("list_notes", {"unexpected": "value"}, db_path=db_path)


def test_update_note_tool_requires_a_change(tmp_path):
    db_path = tmp_path / "brain.db"
    created = run_tool("create_note", {"title": "Existing"}, db_path=db_path)

    with pytest.raises(ValidationError):
        run_tool("update_note", {"note_id": created.id}, db_path=db_path)


def test_run_tool_rejects_unknown_tool(tmp_path):
    db_path = tmp_path / "brain.db"

    with pytest.raises(ValueError, match="Unknown tool"):
        run_tool("missing_tool", {}, db_path=db_path)
