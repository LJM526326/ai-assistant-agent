import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "assistant.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        content TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL,
        content TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


# -------- Notes --------
def add_note(content: str) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes(created_at, content) VALUES(?, ?)",
        (datetime.utcnow().isoformat(), content.strip()),
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return note_id


def list_notes(limit: int = 20):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, created_at, content FROM notes ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows


def search_notes(query: str, limit: int = 20):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, created_at, content FROM notes WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
        (f"%{query}%", limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# -------- Tasks --------
def add_task(content: str) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks(created_at, status, content) VALUES(?, 'open', ?)",
        (datetime.utcnow().isoformat(), content.strip()),
    )
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return task_id


def list_tasks(status: str = "open", limit: int = 50):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, created_at, status, content FROM tasks WHERE status = ? ORDER BY id DESC LIMIT ?",
        (status, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def close_task(task_id: int) -> bool:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET status='done' WHERE id=?",
        (task_id,),
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


# -------- Long-term profile memory --------
def set_memory(key: str, value: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO memory(key, value, updated_at)
        VALUES(?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        """,
        (key.strip(), value.strip(), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_memory(key: str):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT key, value, updated_at FROM memory WHERE key=?", (key.strip(),))
    row = cur.fetchone()
    conn.close()
    return row


def all_memory():
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT key, value, updated_at FROM memory ORDER BY updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows
