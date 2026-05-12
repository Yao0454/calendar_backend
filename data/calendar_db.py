"""Server-side SQLite storage for per-user events and todos."""

import json
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
            CREATE TABLE IF NOT EXISTS arxiv_preferences (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL UNIQUE,
                push_time       TEXT    DEFAULT '09:00',  -- HH:MM 格式
                paper_count     INTEGER DEFAULT 5,        -- 每天推荐多少篇
                categories      TEXT    NOT NULL,         -- JSON: ["cs.AI", "cs.CV"]
                is_enabled      INTEGER DEFAULT 1,        -- 是否启用推送
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS papers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                arxiv_id        TEXT    NOT NULL UNIQUE,  -- arXiv 唯一 ID
                user_id         TEXT,                     -- 如果 NULL 表示全局论文，如果有值表示用户已保存
                title           TEXT    NOT NULL,
                authors         TEXT    NOT NULL,         -- JSON 格式
                abstract        TEXT,
                pdf_url         TEXT,
                category        TEXT    NOT NULL,         -- cs.AI, cs.CV 等
                published_date  TEXT    NOT NULL,         -- YYYY-MM-DD
                paper_text      TEXT,                     -- PDF 转文本内容
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS daily_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         TEXT    NOT NULL,
                report_date     TEXT    NOT NULL,         -- YYYY-MM-DD
                summary         TEXT    NOT NULL,         -- 日报摘要
                paper_ids       TEXT    NOT NULL,         -- JSON: [1, 2, 3, ...]
                html_content    TEXT,                     -- HTML 格式日报
                pdf_filename    TEXT,                     -- 存储文件名
                download_count  INTEGER DEFAULT 0,        -- 下载次数统计
                created_at      TEXT    NOT NULL,
                updated_at      TEXT    NOT NULL,
                UNIQUE(user_id, report_date)
            );
            CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_id);
            CREATE INDEX IF NOT EXISTS idx_todos_user  ON todos(user_id);
            CREATE INDEX IF NOT EXISTS idx_arxiv_pref_user ON arxiv_preferences(user_id);
            CREATE INDEX IF NOT EXISTS idx_papers_arxiv ON papers(arxiv_id);
            CREATE INDEX IF NOT EXISTS idx_papers_user ON papers(user_id);
            CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_date);
            CREATE INDEX IF NOT EXISTS idx_reports_user ON daily_reports(user_id);
            CREATE INDEX IF NOT EXISTS idx_reports_date ON daily_reports(report_date);
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
            (
                user_id,
                data["title"],
                data.get("date"),
                data.get("time"),
                data.get("location"),
                data.get("notes"),
                0,
                now,
                now,
            ),
        )
        return dict(
            c.execute("SELECT * FROM events WHERE id=?", (cur.lastrowid,)).fetchone()
        )


def update_event(event_id: int, user_id: str, data: dict) -> dict | None:
    now = _now()
    with _conn() as c:
        c.execute(
            "UPDATE events SET title=?,date=?,time=?,location=?,notes=?,is_pinned=?,updated_at=?"
            " WHERE id=? AND user_id=?",
            (
                data["title"],
                data.get("date"),
                data.get("time"),
                data.get("location"),
                data.get("notes"),
                1 if data.get("is_pinned") else 0,
                now,
                event_id,
                user_id,
            ),
        )
        row = c.execute(
            "SELECT * FROM events WHERE id=? AND user_id=?", (event_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def delete_event(event_id: int, user_id: str) -> bool:
    with _conn() as c:
        return (
            c.execute(
                "DELETE FROM events WHERE id=? AND user_id=?", (event_id, user_id)
            ).rowcount
            > 0
        )


def set_event_pinned(event_id: int, user_id: str, is_pinned: bool) -> bool:
    with _conn() as c:
        return (
            c.execute(
                "UPDATE events SET is_pinned=?,updated_at=? WHERE id=? AND user_id=?",
                (1 if is_pinned else 0, _now(), event_id, user_id),
            ).rowcount
            > 0
        )


def bulk_insert_events(user_id: str, events: list[dict]) -> list[dict]:
    now = _now()
    result = []
    with _conn() as c:
        for e in events:
            cur = c.execute(
                "INSERT INTO events(user_id,title,date,time,location,notes,is_pinned,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    e.get("title", ""),
                    e.get("date"),
                    e.get("time"),
                    e.get("location"),
                    e.get("notes"),
                    0,
                    now,
                    now,
                ),
            )
            result.append(
                dict(
                    c.execute(
                        "SELECT * FROM events WHERE id=?", (cur.lastrowid,)
                    ).fetchone()
                )
            )
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
            (
                user_id,
                data["title"],
                data.get("deadline"),
                data.get("priority") or "medium",
                data.get("notes"),
                0,
                0,
                now,
                now,
            ),
        )
        return dict(
            c.execute("SELECT * FROM todos WHERE id=?", (cur.lastrowid,)).fetchone()
        )


def update_todo(todo_id: int, user_id: str, data: dict) -> dict | None:
    now = _now()
    with _conn() as c:
        c.execute(
            "UPDATE todos SET title=?,deadline=?,priority=?,notes=?,is_done=?,is_pinned=?,updated_at=?"
            " WHERE id=? AND user_id=?",
            (
                data["title"],
                data.get("deadline"),
                data.get("priority") or "medium",
                data.get("notes"),
                1 if data.get("is_done") else 0,
                1 if data.get("is_pinned") else 0,
                now,
                todo_id,
                user_id,
            ),
        )
        row = c.execute(
            "SELECT * FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)
        ).fetchone()
        return dict(row) if row else None


def delete_todo(todo_id: int, user_id: str) -> bool:
    with _conn() as c:
        return (
            c.execute(
                "DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)
            ).rowcount
            > 0
        )


def set_todo_done(todo_id: int, user_id: str, is_done: bool) -> bool:
    with _conn() as c:
        return (
            c.execute(
                "UPDATE todos SET is_done=?,updated_at=? WHERE id=? AND user_id=?",
                (1 if is_done else 0, _now(), todo_id, user_id),
            ).rowcount
            > 0
        )


def set_todo_pinned(todo_id: int, user_id: str, is_pinned: bool) -> bool:
    with _conn() as c:
        return (
            c.execute(
                "UPDATE todos SET is_pinned=?,updated_at=? WHERE id=? AND user_id=?",
                (1 if is_pinned else 0, _now(), todo_id, user_id),
            ).rowcount
            > 0
        )


def bulk_insert_todos(user_id: str, todos: list[dict]) -> list[dict]:
    now = _now()
    result = []
    with _conn() as c:
        for t in todos:
            cur = c.execute(
                "INSERT INTO todos(user_id,title,deadline,priority,notes,is_done,is_pinned,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    user_id,
                    t.get("title", ""),
                    t.get("deadline"),
                    t.get("priority") or "medium",
                    t.get("notes"),
                    0,
                    0,
                    now,
                    now,
                ),
            )
            result.append(
                dict(
                    c.execute(
                        "SELECT * FROM todos WHERE id=?", (cur.lastrowid,)
                    ).fetchone()
                )
            )
    return result


# ── arxiv ─────────────────────────────────────────────────────────────────────
def get_arxiv_preference(user_id: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM arxiv_preferences WHERE user_id=?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def create_or_update_arxiv_preference(user_id: str, data: dict) -> dict:
    now = _now()
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM arxiv_preferences WHERE user_id=?", (user_id,)
        ).fetchone()

        if existing:
            c.execute(
                """UPDATE arxiv_preferences
                   SET push_time=?, paper_count=?, categories=?, is_enabled=?, updated_at=?
                   WHERE user_id=?""",
                (
                    data.get("push_time", "09:00"),
                    data.get("paper_count", 5),
                    json.dumps(data.get("categories", [])),
                    1 if data.get("is_enabled", True) else 0,
                    now,
                    user_id,
                ),
            )
        else:
            c.execute(
                """INSERT INTO arxiv_preferences(user_id, push_time, paper_count, categories, is_enabled, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    data.get("push_time", "09:00"),
                    data.get("paper_count", 5),
                    json.dumps(data.get("categories", [])),
                    1 if data.get("is_enabled", True) else 0,
                    now,
                    now,
                ),
            )

        row = c.execute(
            "SELECT * FROM arxiv_preferences WHERE user_id=?", (user_id,)
        ).fetchone()
        return dict(row) if row else {}


def create_or_update_paper(data: dict) -> dict:
    now = _now()
    with _conn() as c:
        existing = c.execute(
            "SELECT id FROM papers WHERE arxiv_id=?", (data["arxiv_id"],)
        ).fetchone()

        if existing:
            c.execute(
                """UPDATE papers
                   SET title=?, authors=?, abstract=?, pdf_url=?, category=?,
                       paper_text=?, updated_at=?
                   WHERE arxiv_id=?""",
                (
                    data.get("title"),
                    data.get("authors"),
                    data.get("abstract"),
                    data.get("pdf_url"),
                    data.get("category"),
                    data.get("paper_text"),
                    now,
                    data["arxiv_id"],
                ),
            )
        else:
            c.execute(
                """INSERT INTO papers(arxiv_id, user_id, title, authors, abstract, pdf_url,
                                     category, published_date, paper_text, created_at, updated_at)
                   VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["arxiv_id"],
                    data.get("user_id"),
                    data.get("title"),
                    json.dumps(data.get("authors", [])),
                    data.get("abstract"),
                    data.get("pdf_url"),
                    data.get("category"),
                    data.get("published_date"),
                    data.get("paper_text"),
                    now,
                    now,
                ),
            )

        row = c.execute(
            "SELECT * FROM papers WHERE arxiv_id=?", (data["arxiv_id"],)
        ).fetchone()
        return dict(row) if row else {}


def get_papers_by_date_and_category(date: str, categories: list[str]) -> list[dict]:
    with _conn() as c:
        placeholders = ",".join("?" * len(categories))
        rows = c.execute(
            f"SELECT * FROM papers WHERE published_date=? AND category IN ({placeholders})",
            [date] + categories,
        ).fetchall()
        return [dict(r) for r in rows]


def create_daily_report(user_id: str, data: dict) -> dict:
    now = _now()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO daily_reports(user_id, report_date, summary, paper_ids, html_content, pdf_filename, created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                data["report_date"],
                data["summary"],
                json.dumps(data.get("paper_ids", [])),
                data.get("html_content"),
                data.get("pdf_filename"),
                now,
                now,
            ),
        )
        return dict(
            c.execute(
                "SELECT * FROM daily_reports WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        )


def get_daily_report(user_id: str, report_date: str) -> dict | None:
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM daily_reports WHERE user_id=? AND report_date=?",
            (user_id, report_date),
        ).fetchone()
        return dict(row) if row else None


def get_daily_reports_list(user_id: str, limit: int = 30) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM daily_reports WHERE user_id=? ORDER BY report_date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def increment_report_download(report_id: int) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE daily_reports SET download_count = download_count + 1 WHERE id=?",
            (report_id,),
        )
