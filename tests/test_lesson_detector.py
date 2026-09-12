from coursera.lesson_detector import LessonDetector, LessonType
from tests.conftest import load_fixture


def test_classifies_video_from_url_and_html():
    detector = LessonDetector()
    html = load_fixture("video.html")
    result = detector.classify(
        "https://www.coursera.org/learn/entrepreneurial-mindset/lecture/abc123",
        html=html,
        visible_text="Week 4 - Customer Discovery Watch this lecture video",
        title="Week 4 - Customer Discovery",
    )
    assert result.lesson_type == LessonType.VIDEO
    assert result.is_confident


def test_classifies_quiz_and_does_not_treat_as_video():
    detector = LessonDetector()
    html = load_fixture("quiz.html")
    result = detector.classify(
        "https://www.coursera.org/learn/entrepreneurial-mindset/quiz/xyz",
        html=html,
        visible_text="Module Quiz Submit Check answers Honor Code",
        title="Module Quiz",
    )
    assert result.lesson_type == LessonType.QUIZ


def test_classifies_reading():
    detector = LessonDetector()
    html = load_fixture("reading.html")
    result = detector.classify(
        "https://www.coursera.org/learn/entrepreneurial-mindset/supplement/aaa",
        html=html,
        visible_text="Reading: Course overview",
        title="Reading: Course overview",
    )
    assert result.lesson_type == LessonType.READING


def test_classifies_assignment():
    detector = LessonDetector()
    html = load_fixture("assignment.html")
    result = detector.classify(
        "https://www.coursera.org/learn/entrepreneurial-mindset/assignment/bbb",
        html=html,
        visible_text="Programming assignment Submit assignment",
        title="Programming assignment",
    )
    assert result.lesson_type == LessonType.ASSIGNMENT


def test_unknown_page():
    detector = LessonDetector()
    html = load_fixture("unknown.html")
    result = detector.classify(
        "https://www.coursera.org/about",
        html=html,
        visible_text="Help Center Contact support",
        title="Unknown page",
    )
    assert result.lesson_type == LessonType.UNKNOWN
