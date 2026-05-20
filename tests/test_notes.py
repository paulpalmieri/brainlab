from brain_lab.notes import (
    create_note,
    delete_note,
    get_note,
    list_notes,
    search_notes,
    update_note,
)


def test_create_note_returns_note(tmp_path):
    db_path = tmp_path / "brain.db"

    note = create_note(
        title="Agent notes",
        body="Learn tool calls.",
        tags=["ai", "mcp"],
        db_path=db_path,
    )

    assert note.id
    assert note.title == "Agent notes"
    assert note.body == "Learn tool calls."
    assert note.tags == ["ai", "mcp"]
    assert note.created_at
    assert note.updated_at


def test_list_notes_returns_created_notes(tmp_path):
    db_path = tmp_path / "brain.db"
    created = create_note(title="First note", db_path=db_path)

    notes = list_notes(db_path=db_path)

    assert len(notes) == 1
    assert notes[0].id == created.id
    assert notes[0].title == "First note"


def test_get_note_returns_created_note(tmp_path):
    db_path = tmp_path / "brain.db"
    created = create_note(
        title="Readable systems",
        body="Keep the data path explicit.",
        tags=["sqlite"],
        db_path=db_path,
    )

    note = get_note(created.id, db_path=db_path)

    assert note is not None
    assert note.id == created.id
    assert note.title == "Readable systems"
    assert note.body == "Keep the data path explicit."
    assert note.tags == ["sqlite"]


def test_get_note_returns_none_for_missing_note(tmp_path):
    db_path = tmp_path / "brain.db"

    note = get_note("missing-note-id", db_path=db_path)

    assert note is None


def test_update_note_updates_existing_note(tmp_path):
    db_path = tmp_path / "brain.db"
    created = create_note(
        title="Draft title",
        body="Draft body",
        tags=["draft"],
        db_path=db_path,
    )

    updated = update_note(
        created.id,
        title="Final title",
        tags="done,notes",
        db_path=db_path,
    )

    assert updated is not None
    assert updated.id == created.id
    assert updated.title == "Final title"
    assert updated.body == "Draft body"
    assert updated.tags == ["done", "notes"]
    assert updated.created_at == created.created_at
    assert updated.updated_at

    stored = get_note(created.id, db_path=db_path)
    assert stored == updated


def test_update_note_returns_none_for_missing_note(tmp_path):
    db_path = tmp_path / "brain.db"

    updated = update_note("missing-note-id", title="New title", db_path=db_path)

    assert updated is None


def test_update_note_can_clear_tags(tmp_path):
    db_path = tmp_path / "brain.db"
    created = create_note(title="Tagged note", tags=["old"], db_path=db_path)

    updated = update_note(created.id, tags="", db_path=db_path)

    assert updated is not None
    assert updated.tags == []


def test_delete_note_removes_existing_note(tmp_path):
    db_path = tmp_path / "brain.db"
    created = create_note(title="Temporary note", db_path=db_path)

    deleted = delete_note(created.id, db_path=db_path)

    assert deleted is True
    assert get_note(created.id, db_path=db_path) is None
    assert list_notes(db_path=db_path) == []


def test_delete_note_returns_false_for_missing_note(tmp_path):
    db_path = tmp_path / "brain.db"

    deleted = delete_note("missing-note-id", db_path=db_path)

    assert deleted is False


def test_search_notes_matches_title_body_and_tags(tmp_path):
    db_path = tmp_path / "brain.db"
    title_match = create_note(title="SQLite basics", db_path=db_path)
    body_match = create_note(
        title="Agent loop",
        body="Tool calls stay explicit.",
        db_path=db_path,
    )
    tag_match = create_note(title="Protocol notes", tags=["mcp"], db_path=db_path)
    create_note(title="Grocery list", body="Buy coffee.", db_path=db_path)

    assert search_notes("sqlite", db_path=db_path) == [title_match]
    assert search_notes("TOOL", db_path=db_path) == [body_match]
    assert search_notes("mcp", db_path=db_path) == [tag_match]


def test_search_notes_returns_empty_list_for_blank_query(tmp_path):
    db_path = tmp_path / "brain.db"
    create_note(title="Existing note", db_path=db_path)

    notes = search_notes("   ", db_path=db_path)

    assert notes == []


def test_tags_round_trip_as_list(tmp_path):
    db_path = tmp_path / "brain.db"

    create_note(title="Tagged note", tags="ai, mcp", db_path=db_path)

    notes = list_notes(db_path=db_path)
    assert notes[0].tags == ["ai", "mcp"]
