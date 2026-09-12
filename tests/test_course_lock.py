from config.settings import Settings
from coursera.course_detector import CourseDetector


def test_only_named_course_matches():
    settings = Settings(course_name="Entrepreneurial Mindset", course_url="")
    detector = CourseDetector(settings)
    assert detector.matches_target(
        "Entrepreneurial Mindset",
        "https://www.coursera.org/learn/entrepreneurial-mindset/lecture/abc",
    )
    assert not detector.matches_target(
        "Machine Learning",
        "https://www.coursera.org/learn/machine-learning/lecture/abc",
    )


def test_url_slug_lock():
    settings = Settings(
        course_name="",
        course_url="https://www.coursera.org/learn/entrepreneurial-mindset",
    )
    detector = CourseDetector(settings)
    assert detector.matches_target(
        "Anything",
        "https://www.coursera.org/learn/entrepreneurial-mindset/home/week/1",
    )
    assert not detector.matches_target(
        "Anything",
        "https://www.coursera.org/learn/other-course/home/week/1",
    )
