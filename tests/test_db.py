import sqlite3

from brain_lab.db import init_db


def test_init_db_creates_notes_table(tmp_path):
    db_path = tmp_path / "brain.db"

    init_db(db_path)

    with sqlite3.connect(db_path) as connection:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'notes'
            """
        ).fetchone()

    assert table is not None

