from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentState(str, Enum):
    STARTING = "STARTING"
    WAITING_FOR_LOGIN = "WAITING_FOR_LOGIN"
    WAITING_FOR_COURSE = "WAITING_FOR_COURSE"
    SCANNING_COURSE = "SCANNING_COURSE"
    DETECTING_LESSON = "DETECTING_LESSON"
    OPENING_VIDEO = "OPENING_VIDEO"
    PLAYING_VIDEO = "PLAYING_VIDEO"
    VERIFYING_COMPLETION = "VERIFYING_COMPLETION"
    SKIPPING_QUIZ = "SKIPPING_QUIZ"
    SKIPPING_READING = "SKIPPING_READING"
    SKIPPING_ASSIGNMENT = "SKIPPING_ASSIGNMENT"
    MOVING_TO_NEXT = "MOVING_TO_NEXT"
    COURSE_COMPLETE = "COURSE_COMPLETE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


ALLOWED_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.STARTING: {
        AgentState.WAITING_FOR_LOGIN,
        AgentState.WAITING_FOR_COURSE,
        AgentState.SCANNING_COURSE,
        AgentState.ERROR,
        AgentState.STOPPED,
        AgentState.PAUSED,
    },
    AgentState.WAITING_FOR_LOGIN: {
        AgentState.WAITING_FOR_COURSE,
        AgentState.SCANNING_COURSE,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.WAITING_FOR_COURSE: {
        AgentState.SCANNING_COURSE,
        AgentState.WAITING_FOR_LOGIN,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.SCANNING_COURSE: {
        AgentState.DETECTING_LESSON,
        AgentState.OPENING_VIDEO,
        AgentState.COURSE_COMPLETE,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
        AgentState.WAITING_FOR_COURSE,
    },
    AgentState.DETECTING_LESSON: {
        AgentState.OPENING_VIDEO,
        AgentState.PLAYING_VIDEO,
        AgentState.SKIPPING_QUIZ,
        AgentState.SKIPPING_READING,
        AgentState.SKIPPING_ASSIGNMENT,
        AgentState.MOVING_TO_NEXT,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
        AgentState.SCANNING_COURSE,
    },
    AgentState.OPENING_VIDEO: {
        AgentState.PLAYING_VIDEO,
        AgentState.DETECTING_LESSON,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.PLAYING_VIDEO: {
        AgentState.VERIFYING_COMPLETION,
        AgentState.PLAYING_VIDEO,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
        AgentState.DETECTING_LESSON,
    },
    AgentState.VERIFYING_COMPLETION: {
        AgentState.MOVING_TO_NEXT,
        AgentState.PLAYING_VIDEO,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.SKIPPING_QUIZ: {AgentState.MOVING_TO_NEXT, AgentState.PAUSED, AgentState.STOPPED, AgentState.ERROR},
    AgentState.SKIPPING_READING: {AgentState.MOVING_TO_NEXT, AgentState.PAUSED, AgentState.STOPPED, AgentState.ERROR},
    AgentState.SKIPPING_ASSIGNMENT: {
        AgentState.MOVING_TO_NEXT,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.MOVING_TO_NEXT: {
        AgentState.DETECTING_LESSON,
        AgentState.SCANNING_COURSE,
        AgentState.COURSE_COMPLETE,
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.COURSE_COMPLETE: {AgentState.STOPPED, AgentState.PAUSED},
    AgentState.PAUSED: {
        AgentState.WAITING_FOR_LOGIN,
        AgentState.WAITING_FOR_COURSE,
        AgentState.SCANNING_COURSE,
        AgentState.DETECTING_LESSON,
        AgentState.PLAYING_VIDEO,
        AgentState.STOPPED,
        AgentState.ERROR,
    },
    AgentState.ERROR: {AgentState.PAUSED, AgentState.STOPPED, AgentState.SCANNING_COURSE, AgentState.DETECTING_LESSON},
    AgentState.STOPPED: set(),
}


class InvalidTransition(Exception):
    pass


def can_transition(current: AgentState, target: AgentState) -> bool:
    if current == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(current, set())


def transition(current: AgentState, target: AgentState) -> AgentState:
    if not can_transition(current, target):
        raise InvalidTransition(f"{current.value} -> {target.value}")
    return target


@dataclass
class RuntimeContext:
    course_name: str = ""
    course_url: str = ""
    course_slug: str = ""
    lesson_title: str = ""
    lesson_type: str = ""
    watch_started_monotonic: float = 0.0
