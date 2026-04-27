"""Server-side SQLite storage for per-user events and todos."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "data" / "calendar.db"


def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                title       TEXT    NOT NULL,
                date        TEXT,
                time        TEXT,
                location    TEXT,
                notes       TEXT,
                is_pinned   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS todos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL,
                title       TEXT    NOT NULL,
                deadline    TEXT,
                priority    TEXT    NOT NULL DEFAULT 'medium',
                notes       TEXT,
                is_done     INTEGER NOT NULL DEFAULT 0,
                is_pinned   INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_todos_user  ON todos(user_id);
        """)


@contextmanager
def _conn():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Events ────────────────────────────────────────────────────────────────────

def get_events(user_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE user_id=? ORDER BY is_pinned DESC, date ASC, time ASC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_event(user_id: str, data: dict) -> dict:
    now = _now()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO events(user_id,title,date,time,location,notes,is_pinned,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, data["title"], data.get("date"), data.get("time"),
             data.get("location"), data.get("notes"), 0, now, now),
        )
        return dict(c.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone())


def update_event(event_id: int, user_id: str, data: dict) -> dict | None:
    now = _now()
    with _conn() as c:
        c.execute(
            "UPDATE events SET title=?,date=?,time=?,location=?,notes=?,is_pinned=?,updated_at=?"
            " WHERE id=? AND user_id=?",
            (data["title"], data.get("date"), data.get("time"), data.get("location"),
             data.get("notes"), 1 if data.get("is_pinned") else 0, now, event_id, user_id),
        )
        row = c.execute("SELECT * FROM events WHERE id=? AND user_id=?", (event_id, user_id)).fetchone()
        return dict(row) if row else None


def delete_event(event_id: int, user_id: str) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM events WHERE id=? AND user_id=?", (event_id, user_id)).rowcount > 0


def set_event_pinned(event_id: int, user_id: str, is_pinned: bool) -> bool:
    with _conn() as c:
        return c.execute(
            "UPDATE events SET is_pinned=?,updated_at=? WHERE id=? AND user_id=?",
            (1 if is_pinned else 0, _now(), event_id, user_id),
        ).rowcount > 0


def bulk_insert_events(user_id: str, events: list[dict]) -> list[dict]:
    now = _now()
    result = []
    with _conn() as c:
        for e in events:
            cur = c.execute(
                "INSERT INTO events(user_id,title,date,time,location,notes,is_pinned,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (user_id, e.get("title", ""), e.get("date"), e.get("time"),
                 e.get("location"), e.get("notes"), 0, now, now),
            )
            result.append(dict(c.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone()))
    return result


# ── Todos ─────────────────────────────────────────────────────────────────────

def get_todos(user_id: str) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM todos WHERE user_id=? ORDER BY is_pinned DESC, is_done ASC, deadline ASC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_todo(user_id: str, data: dict) -> dict:
    now = _now()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO todos(user_id,title,deadline,priority,notes,is_done,is_pinned,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, data["title"], data.get("deadline"), data.get("priority", "medium"),
             data.get("notes"), 0, 0, now, now),
        )
        return dict(c.execute("SELECT * FROM todos WHERE id=?", (cur.lastrowid,)).fetchone())


def update_todo(todo_id: int, user_id: str, data: dict) -> dict | None:
    now = _now()
    with _conn() as c:
        c.execute(
            "UPDATE todos SET title=?,deadline=?,priority=?,notes=?,is_done=?,is_pinned=?,updated_at=?"
            " WHERE id=? AND user_id=?",
            (data["title"], data.get("deadline"), data.get("priority", "medium"),
             data.get("notes"), 1 if data.get("is_done") else 0,
             1 if data.get("is_pinned") else 0, now, todo_id, user_id),
        )
        row = c.execute("SELECT * FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)).fetchone()
        return dict(row) if row else None


def delete_todo(todo_id: int, user_id: str) -> bool:
    with _conn() as c:
        return c.execute("DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)).rowcount > 0


def set_todo_done(todo_id: int, user_id: str, is_done: bool) -> bool:
    with _conn() as c:
        return c.execute(
            "UPDATE todos SET is_done=?,updated_at=? WHERE id=? AND user_id=?",
            (1 if is_done else 0, _now(), todo_id, user_id),
        ).rowcount > 0


def set_todo_pinned(todo_id: int, user_id: str, is_pinned: bool) -> bool:
    with _conn() as c:
        return c.execute(
            "UPDATE todos SET is_pinned=?,updated_at=? WHERE id=? AND user_id=?",
            (1 if is_pinned else 0, _now(), todo_id, user_id),
        ).rowcount > 0


def bulk_insert_todos(user_id: str, todos: list[dict]) -> list[dict]:
    now = _now()
    result = []
    with _conn() as c:
        for t in todos:
            cur = c.execute(
                "INSERT INTO todos(user_id,title,deadline,priority,notes,is_done,is_pinned,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (user_id, t.get("title", ""), t.get("deadline"),
                 t.get("priority", "medium"), t.get("notes"), 0, 0, now, now),
            )
            result.append(dict(c.execute("SELECT * FROM todos WHERE id=?", (cur.lastrowid,)).fetchone()))
    return result
