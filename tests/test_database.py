from pathlib import Path

from database.database import Database
from database.models import LessonRecord, LessonStatus
from utils.helpers import backoff_seconds


def test_backoff_schedule():
    assert backoff_seconds(1) == 2
    assert backoff_seconds(2) == 5
    assert backoff_seconds(3) == 10
    assert backoff_seconds(9) == 10


def test_lesson_upsert_and_resume(tmp_path: Path):
    db = Database(tmp_path / "progress.db")
    record = LessonRecord(
        course="Entrepreneurial Mindset",
        course_url="https://www.coursera.org/learn/entrepreneurial-mindset",
        lesson="Customer Discovery",
        lesson_url="https://www.coursera.org/learn/entrepreneurial-mindset/lecture/abc",
        lesson_type="VIDEO",
        status=LessonStatus.PLAYING,
        started_at="2026-01-01T00:00:00+00:00",
    )
    db.upsert_lesson(record)
    loaded = db.get_lesson(record.lesson_url)
    assert loaded is not None
    assert loaded.status == LessonStatus.PLAYING

    record.status = LessonStatus.COMPLETED
    record.completed_at = "2026-01-01T00:10:00+00:00"
    db.upsert_lesson(record)
    loaded = db.get_lesson(record.lesson_url)
    assert loaded.status == LessonStatus.COMPLETED
    completed, total = db.video_counts(record.course_url)
    assert (completed, total) == (1, 1)
    db.close()
