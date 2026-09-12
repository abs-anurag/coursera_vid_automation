from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LessonStatus(str, Enum):
    PENDING = "PENDING"
    PLAYING = "PLAYING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"


class ControlCommand(str, Enum):
    NONE = "NONE"
    CONTINUE = "CONTINUE"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP = "STOP"


@dataclass
class LessonRecord:
    course: str
    course_url: str
    lesson: str
    lesson_url: str
    lesson_type: str
    status: LessonStatus
    started_at: str | None = None
    completed_at: str | None = None
    last_seen: str | None = None
    id: int | None = None
