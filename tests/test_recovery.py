from agent.decision_engine import DecisionEngine
from agent.recovery import Recovery, RecoveryExhausted
from agent.state import AgentState
from coursera.lesson_detector import Classification, LessonType
from utils.helpers import backoff_seconds


def test_backoff_sequence() -> None:
    assert [backoff_seconds(i) for i in (1, 2, 3, 4)] == [2, 5, 10, 10]


def test_recovery_exhausts(monkeypatch) -> None:
    recovery = Recovery(max_retries=3)

    async def _sleep(_delay):
        return None

    monkeypatch.setattr("agent.recovery.asyncio.sleep", _sleep)

    import asyncio

    async def run():
        await recovery.wait()
        await recovery.wait()
        await recovery.wait()
        try:
            await recovery.wait()
        except RecoveryExhausted:
            return True
        return False

    assert asyncio.run(run()) is True


def test_decision_skips_quiz_and_stops_unknown() -> None:
    engine = DecisionEngine()
    quiz = engine.decide(Classification(LessonType.QUIZ, 0.9, ["url"], "Quiz"), AgentState.DETECTING_LESSON)
    assert quiz == AgentState.SKIPPING_QUIZ
    unknown = engine.decide(Classification(LessonType.UNKNOWN, 0.2, [], ""), AgentState.DETECTING_LESSON)
    assert unknown == AgentState.ERROR
    video = engine.decide(Classification(LessonType.VIDEO, 0.8, ["url"], "Lecture"), AgentState.DETECTING_LESSON)
    assert video == AgentState.OPENING_VIDEO
