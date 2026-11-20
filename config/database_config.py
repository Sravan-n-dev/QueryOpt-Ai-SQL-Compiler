"""
QueryOpt AI — Database Connection Configuration
===============================================
Manages database initialization, schema creation, deterministic seeding,
and transactional / read-only SQLite connections.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from config.settings import get_settings
from database.seed import is_seeded, seed_database


def get_connection(readonly: bool = False) -> sqlite3.Connection:
    """Return an active connection to the SQLite College database."""
    settings = get_settings()
    db_path: Path = settings.database_path

    if not db_path.exists():
        initialize_database()

    if readonly:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_readonly_connection() -> sqlite3.Connection:
    """Return a strictly read-only SQLite connection."""
    return get_connection(readonly=True)


def initialize_database(force: bool = False) -> None:
    """Initialize the College Database with schema and deterministic seed data."""
    settings = get_settings()
    db_path: Path = settings.database_path
    schema_path = settings.project_root / "database" / "schema.sql"

    if force and db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        if not is_seeded(conn) or force:
            # Read schema.sql
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            seed_database(conn)
            conn.commit()
    finally:
        conn.close()
