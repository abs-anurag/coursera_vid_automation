from __future__ import annotations

from coursera.lesson_detector import Classification, LessonType
from agent.state import AgentState


class DecisionEngine:
    def decide(self, classification: Classification, current: AgentState) -> AgentState:
        if not classification.is_confident:
            return AgentState.ERROR
        mapping = {
            LessonType.VIDEO: AgentState.OPENING_VIDEO if current != AgentState.PLAYING_VIDEO else AgentState.PLAYING_VIDEO,
            LessonType.QUIZ: AgentState.SKIPPING_QUIZ,
            LessonType.READING: AgentState.SKIPPING_READING,
            LessonType.ASSIGNMENT: AgentState.SKIPPING_ASSIGNMENT,
            LessonType.UNKNOWN: AgentState.ERROR,
        }
        if current in {AgentState.DETECTING_LESSON, AgentState.SCANNING_COURSE, AgentState.MOVING_TO_NEXT}:
            if classification.lesson_type == LessonType.VIDEO:
                return AgentState.OPENING_VIDEO
        return mapping[classification.lesson_type]
