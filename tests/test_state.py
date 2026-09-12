from agent.decision_engine import DecisionEngine
from agent.state import AgentState, can_transition, transition
from coursera.lesson_detector import Classification, LessonType


def test_allowed_playing_to_verifying():
    assert can_transition(AgentState.PLAYING_VIDEO, AgentState.VERIFYING_COMPLETION)
    assert transition(AgentState.PLAYING_VIDEO, AgentState.VERIFYING_COMPLETION) == AgentState.VERIFYING_COMPLETION


def test_stop_has_no_outbound_transitions():
    assert not can_transition(AgentState.STOPPED, AgentState.PLAYING_VIDEO)


def test_decision_engine_skips_quiz():
    engine = DecisionEngine()
    classification = Classification(LessonType.QUIZ, 0.9, ["url"], "Quiz")
    assert engine.decide(classification, AgentState.DETECTING_LESSON) == AgentState.SKIPPING_QUIZ


def test_decision_engine_opens_video():
    engine = DecisionEngine()
    classification = Classification(LessonType.VIDEO, 0.9, ["url"], "Lecture")
    assert engine.decide(classification, AgentState.DETECTING_LESSON) == AgentState.OPENING_VIDEO


def test_unknown_is_error():
    engine = DecisionEngine()
    classification = Classification(LessonType.UNKNOWN, 0.1, [], "")
    assert engine.decide(classification, AgentState.DETECTING_LESSON) == AgentState.ERROR
