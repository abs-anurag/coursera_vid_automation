from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from database.models import ControlCommand, LessonRecord, LessonStatus
from utils.helpers import utc_now_iso
from utils.logger import get_logger

log = get_logger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course TEXT NOT NULL,
    course_url TEXT NOT NULL,
    lesson TEXT NOT NULL,
    lesson_url TEXT NOT NULL UNIQUE,
    lesson_type TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    message TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO'
);

CREATE TABLE IF NOT EXISTS control (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    command TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    course TEXT,
    course_url TEXT,
    current_lesson TEXT,
    current_type TEXT,
    agent_state TEXT,
    videos_completed INTEGER DEFAULT 0,
    videos_total INTEGER DEFAULT 0,
    elapsed_seconds REAL DEFAULT 0,
    updated_at TEXT
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.execute(
                "INSERT OR IGNORE INTO control (id, command, updated_at) VALUES (1, ?, ?)",
                (ControlCommand.NONE.value, utc_now_iso()),
            )
            self._conn.execute(
                "INSERT OR IGNORE INTO runtime (id, agent_state, updated_at) VALUES (1, ?, ?)",
                ("STOPPED", utc_now_iso()),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def add_event(self, message: str, level: str = "INFO") -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (created_at, message, level) VALUES (?, ?, ?)",
                (utc_now_iso(), message, level),
            )
            self._conn.commit()

    def recent_events(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT created_at, message, level FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_command(self, command: ControlCommand) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE control SET command = ?, updated_at = ? WHERE id = 1",
                (command.value, utc_now_iso()),
            )
            self._conn.commit()

    def pop_command(self) -> ControlCommand:
        with self._lock:
            row = self._conn.execute("SELECT command FROM control WHERE id = 1").fetchone()
            command = ControlCommand(row["command"] if row else ControlCommand.NONE.value)
            if command != ControlCommand.NONE:
                self._conn.execute(
                    "UPDATE control SET command = ?, updated_at = ? WHERE id = 1",
                    (ControlCommand.NONE.value, utc_now_iso()),
                )
                self._conn.commit()
            return command

    def peek_command(self) -> ControlCommand:
        with self._lock:
            row = self._conn.execute("SELECT command FROM control WHERE id = 1").fetchone()
        return ControlCommand(row["command"] if row else ControlCommand.NONE.value)

    def upsert_lesson(self, record: LessonRecord) -> None:
        now = utc_now_iso()
        record.last_seen = now
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO lessons (
                    course, course_url, lesson, lesson_url, lesson_type, status,
                    started_at, completed_at, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lesson_url) DO UPDATE SET
                    course = excluded.course,
                    course_url = excluded.course_url,
                    lesson = excluded.lesson,
                    lesson_type = excluded.lesson_type,
                    status = excluded.status,
                    started_at = COALESCE(excluded.started_at, lessons.started_at),
                    completed_at = COALESCE(excluded.completed_at, lessons.completed_at),
                    last_seen = excluded.last_seen
                """,
                (
                    record.course,
                    record.course_url,
                    record.lesson,
                    record.lesson_url,
                    record.lesson_type,
                    record.status.value,
                    record.started_at,
                    record.completed_at,
                    record.last_seen,
                ),
            )
            self._conn.commit()

    def get_lesson(self, lesson_url: str) -> LessonRecord | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM lessons WHERE lesson_url = ?",
                (lesson_url,),
            ).fetchone()
        return self._row_to_lesson(row) if row else None

    def lessons_for_course(self, course_url: str) -> list[LessonRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM lessons WHERE course_url = ? ORDER BY id",
                (course_url,),
            ).fetchall()
        return [self._row_to_lesson(row) for row in rows]

    def video_counts(self, course_url: str) -> tuple[int, int]:
        with self._lock:
            total = self._conn.execute(
                "SELECT COUNT(*) AS n FROM lessons WHERE course_url = ? AND lesson_type = 'VIDEO'",
                (course_url,),
            ).fetchone()["n"]
            completed = self._conn.execute(
                """
                SELECT COUNT(*) AS n FROM lessons
                WHERE course_url = ? AND lesson_type = 'VIDEO' AND status = ?
                """,
                (course_url, LessonStatus.COMPLETED.value),
            ).fetchone()["n"]
        return completed, total

    def update_runtime(self, **fields) -> None:
        allowed = {
            "course",
            "course_url",
            "current_lesson",
            "current_type",
            "agent_state",
            "videos_completed",
            "videos_total",
            "elapsed_seconds",
        }
        assignments = []
        values = []
        for key, value in fields.items():
            if key in allowed:
                assignments.append(f"{key} = ?")
                values.append(value)
        if not assignments:
            return
        assignments.append("updated_at = ?")
        values.append(utc_now_iso())
        with self._lock:
            self._conn.execute(f"UPDATE runtime SET {', '.join(assignments)} WHERE id = 1", values)
            self._conn.commit()

    def get_runtime(self) -> dict:
        with self._lock:
            row = self._conn.execute("SELECT * FROM runtime WHERE id = 1").fetchone()
        return dict(row) if row else {}

    @staticmethod
    def _row_to_lesson(row: sqlite3.Row) -> LessonRecord:
        return LessonRecord(
            id=row["id"],
            course=row["course"],
            course_url=row["course_url"],
            lesson=row["lesson"],
            lesson_url=row["lesson_url"],
            lesson_type=row["lesson_type"],
            status=LessonStatus(row["status"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            last_seen=row["last_seen"],
        )
