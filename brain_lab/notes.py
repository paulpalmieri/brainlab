from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Row
from uuid import uuid4

from brain_lab.db import DEFAULT_DB_PATH, get_connection, init_db
from brain_lab.models import Note


def create_note(
    title: str,
    body: str = "",
    tags: Iterable[str] | str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Note:
    init_db(db_path)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    note = Note(
        id=str(uuid4()),
        title=title,
        body=body,
        tags=_normalize_tags(tags),
        created_at=now,
        updated_at=now,
    )

    with get_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO notes (id, title, body, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                note.id,
                note.title,
                note.body,
                _tags_to_text(note.tags),
                note.created_at,
                note.updated_at,
            ),
        )
        connection.commit()

    return note


def list_notes(db_path: str | Path = DEFAULT_DB_PATH) -> list[Note]:
    init_db(db_path)

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, body, tags, created_at, updated_at
            FROM notes
            ORDER BY created_at ASC
            """
        ).fetchall()

    return [_row_to_note(row) for row in rows]


def get_note(note_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> Note | None:
    init_db(db_path)

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, title, body, tags, created_at, updated_at
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_note(row)


def update_note(
    note_id: str,
    title: str | None = None,
    body: str | None = None,
    tags: Iterable[str] | str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> Note | None:
    existing_note = get_note(note_id, db_path=db_path)

    if existing_note is None:
        return None

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    updated_note = Note(
        id=existing_note.id,
        title=existing_note.title if title is None else title,
        body=existing_note.body if body is None else body,
        tags=existing_note.tags if tags is None else _normalize_tags(tags),
        created_at=existing_note.created_at,
        updated_at=now,
    )

    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE notes
            SET title = ?, body = ?, tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updated_note.title,
                updated_note.body,
                _tags_to_text(updated_note.tags),
                updated_note.updated_at,
                updated_note.id,
            ),
        )
        connection.commit()

    return updated_note


def delete_note(note_id: str, db_path: str | Path = DEFAULT_DB_PATH) -> bool:
    init_db(db_path)

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM notes
            WHERE id = ?
            """,
            (note_id,),
        )
        connection.commit()

    return cursor.rowcount > 0


def search_notes(query: str, db_path: str | Path = DEFAULT_DB_PATH) -> list[Note]:
    init_db(db_path)

    normalized_query = query.strip().lower()
    if not normalized_query:
        return []

    pattern = f"%{normalized_query}%"

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, title, body, tags, created_at, updated_at
            FROM notes
            WHERE lower(title) LIKE ?
                OR lower(body) LIKE ?
                OR lower(tags) LIKE ?
            ORDER BY created_at ASC
            """,
            (pattern, pattern, pattern),
        ).fetchall()

    return [_row_to_note(row) for row in rows]


def _normalize_tags(tags: Iterable[str] | str | None) -> list[str]:
    if tags is None:
        return []

    if isinstance(tags, str):
        raw_tags = tags.split(",")
    else:
        raw_tags = tags

    return [tag.strip() for tag in raw_tags if tag.strip()]


def _tags_to_text(tags: list[str]) -> str:
    return ",".join(tags)


def _row_to_note(row: Row) -> Note:
    return Note(
        id=row["id"],
        title=row["title"],
        body=row["body"],
        tags=_normalize_tags(row["tags"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
