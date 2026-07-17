import asyncio
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import partial
from typing import Any, Callable, TypeVar

from config import DB_PATH

T = TypeVar("T")

_BUSY_RETRIES = 8
_BUSY_SLEEP_SEC = 0.05


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_db_directory() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")


@contextmanager
def get_conn():
    ensure_db_directory()
    conn = sqlite3.connect(str(DB_PATH), timeout=5.0, check_same_thread=False)
    try:
        _configure_connection(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _with_busy_retry(operation: Callable[[], T]) -> T:
    last_err: Exception | None = None
    for attempt in range(_BUSY_RETRIES):
        try:
            return operation()
        except sqlite3.OperationalError as err:
            last_err = err
            if "locked" not in str(err).lower() or attempt == _BUSY_RETRIES - 1:
                raise
            time.sleep(_BUSY_SLEEP_SEC * (attempt + 1))
    assert last_err is not None
    raise last_err


async def run_async(func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Выполняет синхронный вызов БД в пуле потоков, не блокируя event loop."""
    if kwargs:
        return await asyncio.to_thread(partial(func, *args, **kwargs))
    return await asyncio.to_thread(func, *args)


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
        _migrate_participants(conn)
        _migrate_indexes(conn)


def _parse_utc(iso: str) -> datetime:
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _migrate_participants(conn: sqlite3.Connection) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(participants)")}
    if "started_at" not in cols:
        conn.execute("ALTER TABLE participants ADD COLUMN started_at TEXT")
    if "duration_sec" not in cols:
        conn.execute("ALTER TABLE participants ADD COLUMN duration_sec INTEGER")


def _migrate_indexes(conn: sqlite3.Connection) -> None:
    # Удаляем возможные дубликаты ответов перед уникальным индексом
    conn.execute(
        """
        DELETE FROM answers
        WHERE id NOT IN (
            SELECT MIN(id) FROM answers
            GROUP BY participant_id, question_id
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_participant_question
        ON answers(participant_id, question_id)
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_participants_test ON participants(test_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_questions_test ON questions(test_id)"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_participants_test_finished
        ON participants(test_id, finished_at)
        """
    )


def _duration_seconds(started_at: str | None, finished_at: str | None) -> int | None:
    if not started_at or not finished_at:
        return None
    return max(0, int((_parse_utc(finished_at) - _parse_utc(started_at)).total_seconds()))


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


def reopen_test(test_id: int) -> None:
    """Открывает завершённый тест заново, без авто-закрытия по старому таймеру."""
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE tests
            SET status = 'active', link_issued_at = ?, results_delay_sec = 0
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
    def _op() -> int:
        with get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO participants (test_id, user_id, display_name, score, started_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (test_id, user_id, display_name, _utcnow()),
            )
            return cur.lastrowid

    return _with_busy_retry(_op)


def has_answer(participant_id: int, question_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM answers
            WHERE participant_id = ? AND question_id = ?
            """,
            (participant_id, question_id),
        ).fetchone()
    return row is not None


def fill_unanswered_as_wrong(participant_id: int, test_id: int) -> None:
    """Пропущенные вопросы считаются неверными — одним запросом."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO answers
                (participant_id, question_id, selected_index, is_correct)
            SELECT ?, q.id, NULL, 0
            FROM questions q
            WHERE q.test_id = ?
              AND NOT EXISTS (
                  SELECT 1 FROM answers a
                  WHERE a.participant_id = ? AND a.question_id = q.id
              )
            """,
            (participant_id, test_id, participant_id),
        )


def try_save_answer(
    participant_id: int,
    question_id: int,
    selected_index: int | None,
    is_correct: bool,
) -> bool:
    """Сохраняет ответ атомарно. False — если ответ уже был."""

    def _op() -> bool:
        with get_conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO answers (participant_id, question_id, selected_index, is_correct)
                    VALUES (?, ?, ?, ?)
                    """,
                    (participant_id, question_id, selected_index, int(is_correct)),
                )
            except sqlite3.IntegrityError:
                return False
            if is_correct:
                conn.execute(
                    "UPDATE participants SET score = score + 1 WHERE id = ?",
                    (participant_id,),
                )
            return True

    return _with_busy_retry(_op)


def save_answer(
    participant_id: int,
    question_id: int,
    selected_index: int | None,
    is_correct: bool,
) -> None:
    try_save_answer(participant_id, question_id, selected_index, is_correct)


def finish_participant(participant_id: int) -> None:
    finished_at = _utcnow()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT started_at FROM participants WHERE id = ?", (participant_id,)
        ).fetchone()
        started_at = row["started_at"] if row else None
        duration_sec = _duration_seconds(started_at, finished_at)
        conn.execute(
            """
            UPDATE participants
            SET finished_at = ?, duration_sec = ?
            WHERE id = ? AND finished_at IS NULL
            """,
            (finished_at, duration_sec, participant_id),
        )


def finalize_incomplete_participants(test_id: int) -> int:
    """Закрывает незавершённые прохождения перед выдачей результатов."""

    def _op() -> int:
        finished_at = _utcnow()
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, started_at FROM participants
                WHERE test_id = ? AND finished_at IS NULL
                """,
                (test_id,),
            ).fetchall()
            if not rows:
                return 0

            for row in rows:
                pid = row["id"]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO answers
                        (participant_id, question_id, selected_index, is_correct)
                    SELECT ?, q.id, NULL, 0
                    FROM questions q
                    WHERE q.test_id = ?
                      AND NOT EXISTS (
                          SELECT 1 FROM answers a
                          WHERE a.participant_id = ? AND a.question_id = q.id
                      )
                    """,
                    (pid, test_id, pid),
                )
                duration_sec = _duration_seconds(row["started_at"], finished_at)
                conn.execute(
                    """
                    UPDATE participants
                    SET finished_at = ?, duration_sec = ?
                    WHERE id = ? AND finished_at IS NULL
                    """,
                    (finished_at, duration_sec, pid),
                )
            return len(rows)

    return _with_busy_retry(_op)


def count_participants(test_id: int) -> tuple[int, int]:
    """Возвращает (всего начали, завершили)."""
    with get_conn() as conn:
        started = conn.execute(
            "SELECT COUNT(*) AS c FROM participants WHERE test_id = ?",
            (test_id,),
        ).fetchone()["c"]
        finished = conn.execute(
            """
            SELECT COUNT(*) AS c FROM participants
            WHERE test_id = ? AND finished_at IS NOT NULL
            """,
            (test_id,),
        ).fetchone()["c"]
    return started, finished


def get_participants_ranked(test_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM participants
            WHERE test_id = ? AND finished_at IS NOT NULL
            ORDER BY score DESC,
                     COALESCE(duration_sec, 999999999) ASC,
                     finished_at ASC
            """,
            (test_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_finished_tests_by_creator(creator_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tests
            WHERE creator_id = ? AND status = 'finished'
            ORDER BY id DESC
            """,
            (creator_id,),
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
