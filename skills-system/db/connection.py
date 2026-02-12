"""SQLite connection for ~/life/life.db."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path.home() / "life" / "life.db"

_schema_initialized = False


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist. Runs once per process."""
    global _schema_initialized
    if _schema_initialized:
        return
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS skill_span (
            span_id TEXT PRIMARY KEY,
            skill TEXT NOT NULL,
            parent_span_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            first_step TEXT,
            last_step TEXT,
            steps TEXT DEFAULT '[]',
            session_id TEXT,
            started_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
            completed_at TEXT,
            suspended_at TEXT
        );
        CREATE TABLE IF NOT EXISTS life_event (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            skill TEXT NOT NULL,
            phase TEXT DEFAULT '',
            event_type TEXT DEFAULT 'phase_enter',
            session_id TEXT DEFAULT '',
            payload TEXT DEFAULT ''
        );
    """)
    _schema_initialized = True


@contextmanager
def open_db():
    """Context-managed SQLite connection. Always closes, even on exception."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_schema(conn)
    try:
        yield conn
    finally:
        conn.close()
