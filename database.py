import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from config import DB_PATH


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_db_directory() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    ensure_db_directory()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                lang TEXT NOT NULL DEFAULT 'ru',
                question_count INTEGER NOT NULL,
                time_per_question INTEGER,
                results_delay_sec INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                link_issued_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                number INTEGER NOT NULL,
                text TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_index INTEGER NOT NULL,
                FOREIGN KEY (test_id) REFERENCES tests(id)
            );

            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                display_name TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                finished_at TEXT,
                UNIQUE(test_id, user_id),
                FOREIGN KEY (test_id) REFERENCES tests(id)
            );

            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_index INTEGER,
                is_correct INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (participant_id) REFERENCES participants(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            );

            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id INTEGER PRIMARY KEY,
                lang TEXT NOT NULL DEFAULT 'ru'
            );
            """
        )


def set_user_lang(user_id: int, lang: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_prefs (user_id, lang) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang",
            (user_id, lang),
        )


def get_user_lang(user_id: int) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT lang FROM user_prefs WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["lang"] if row else "ru"


def create_test(
    creator_id: int,
    name: str,
    lang: str,
    question_count: int,
    time_per_question: int | None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO tests
            (creator_id, name, lang, question_count, time_per_question,
             results_delay_sec, status, created_at)
            VALUES (?, ?, ?, ?, ?, 0, 'draft', ?)
            """,
            (
                creator_id,
                name,
                lang,
                question_count,
                time_per_question,
                _utcnow(),
            ),
        )
        return cur.lastrowid


def set_results_delay(test_id: int, delay_sec: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE tests SET results_delay_sec = ? WHERE id = ?",
            (delay_sec, test_id),
        )


def add_question(
    test_id: int,
    number: int,
    text: str,
    options: list[str],
    correct_index: int,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO questions (test_id, number, text, options, correct_index)
            VALUES (?, ?, ?, ?, ?)
            """,
            (test_id, number, text, json.dumps(options, ensure_ascii=False), correct_index),
        )
        return cur.lastrowid


def activate_test(test_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE tests SET status = 'active', link_issued_at = ?
            WHERE id = ?
            """,
            (_utcnow(), test_id),
        )


def finish_test(test_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE tests SET status = 'finished' WHERE id = ?", (test_id,)
        )


def get_test(test_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
    return dict(row) if row else None


def get_questions(test_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM questions WHERE test_id = ? ORDER BY number",
            (test_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["options"] = json.loads(d["options"])
        result.append(d)
    return result


def has_completed_participation(test_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM participants
            WHERE test_id = ? AND user_id = ? AND finished_at IS NOT NULL
            """,
            (test_id, user_id),
        ).fetchone()
    return row is not None


def reset_incomplete_participation(test_id: int, user_id: int) -> None:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id FROM participants
            WHERE test_id = ? AND user_id = ? AND finished_at IS NULL
            """,
            (test_id, user_id),
        ).fetchall()
        for row in rows:
            pid = row["id"]
            conn.execute("DELETE FROM answers WHERE participant_id = ?", (pid,))
            conn.execute("DELETE FROM participants WHERE id = ?", (pid,))


def create_participant(test_id: int, user_id: int, display_name: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO participants (test_id, user_id, display_name, score)
            VALUES (?, ?, ?, 0)
            """,
            (test_id, user_id, display_name),
        )
        return cur.lastrowid


def save_answer(
    participant_id: int,
    question_id: int,
    selected_index: int | None,
    is_correct: bool,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO answers (participant_id, question_id, selected_index, is_correct)
            VALUES (?, ?, ?, ?)
            """,
            (participant_id, question_id, selected_index, int(is_correct)),
        )
        if is_correct:
            conn.execute(
                "UPDATE participants SET score = score + 1 WHERE id = ?",
                (participant_id,),
            )


def finish_participant(participant_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE participants SET finished_at = ? WHERE id = ?",
            (_utcnow(), participant_id),
        )


def get_participants_ranked(test_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM participants
            WHERE test_id = ? AND finished_at IS NOT NULL
            ORDER BY score DESC, finished_at ASC
            """,
            (test_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_active_tests_by_creator(creator_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tests
            WHERE creator_id = ? AND status = 'active'
            ORDER BY link_issued_at DESC
            """,
            (creator_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_active_tests_past_deadline() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tests WHERE status = 'active' AND link_issued_at IS NOT NULL"
        ).fetchall()
    now = datetime.now(timezone.utc)
    due = []
    for row in rows:
        test = dict(row)
        issued = datetime.fromisoformat(test["link_issued_at"])
        if issued.tzinfo is None:
            issued = issued.replace(tzinfo=timezone.utc)
        delay = test["results_delay_sec"]
        if delay is None or delay <= 0:
            continue
        elapsed = (now - issued).total_seconds()
        if elapsed >= delay:
            due.append(test)
    return due
