from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

from browser.selectors import SELECTORS
from utils.helpers import normalize_text


class LessonType(str, Enum):
    VIDEO = "VIDEO"
    QUIZ = "QUIZ"
    READING = "READING"
    ASSIGNMENT = "ASSIGNMENT"
    UNKNOWN = "UNKNOWN"


@dataclass
class Classification:
    lesson_type: LessonType
    confidence: float
    evidence: list[str] = field(default_factory=list)
    title: str = ""

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6 and self.lesson_type != LessonType.UNKNOWN


class LessonDetector:
    VIDEO_TEXT = ("video", "lecture", "watch", "transcript")
    QUIZ_TEXT = ("quiz", "exam", "check answers", "honor code", "multiple choice", "submit")
    READING_TEXT = ("reading", "overview", "article", "supplement")
    ASSIGNMENT_TEXT = (
        "assignment",
        "peer-graded",
        "programming assignment",
        "submit assignment",
        "lab",
        "notebook",
    )

    def classify(self, url: str, html: str = "", visible_text: str = "", title: str = "") -> Classification:
        evidence: list[str] = []
        scores: dict[LessonType, float] = {kind: 0.0 for kind in LessonType if kind != LessonType.UNKNOWN}
        path = urlparse(url).path
        text = normalize_text(f"{title} {visible_text}")
        html_l = html.lower()

        if SELECTORS.lecture_url_pattern.search(path):
            scores[LessonType.VIDEO] += 0.7
            evidence.append("url:/lecture/")
        if SELECTORS.quiz_url_pattern.search(path):
            scores[LessonType.QUIZ] += 0.75
            evidence.append("url:quiz/exam")
        if SELECTORS.reading_url_pattern.search(path):
            scores[LessonType.READING] += 0.7
            evidence.append("url:supplement")
        if SELECTORS.assignment_url_pattern.search(path):
            scores[LessonType.ASSIGNMENT] += 0.75
            evidence.append("url:assignment")

        if "<video" in html_l or "video-js" in html_l or 'class="vjs-' in html_l:
            scores[LessonType.VIDEO] += 0.35
            evidence.append("dom:video")
        if any(token in text for token in self.VIDEO_TEXT):
            scores[LessonType.VIDEO] += 0.1

        if any(token in text for token in ("submit", "check answers", "multiple choice")):
            scores[LessonType.QUIZ] += 0.2
            evidence.append("text:quiz-controls")
        if "radiogroup" in html_l or 'type="radio"' in html_l:
            scores[LessonType.QUIZ] += 0.2
            evidence.append("dom:radio")
        if any(token in text for token in self.QUIZ_TEXT):
            scores[LessonType.QUIZ] += 0.1

        if "cml-viewer" in html_l or "<article" in html_l:
            scores[LessonType.READING] += 0.15
            evidence.append("dom:article")
        if any(token in text for token in self.READING_TEXT) and scores[LessonType.VIDEO] < 0.7:
            scores[LessonType.READING] += 0.15

        if any(token in text for token in self.ASSIGNMENT_TEXT):
            scores[LessonType.ASSIGNMENT] += 0.2
            evidence.append("text:assignment")
        if "submit assignment" in text:
            scores[LessonType.ASSIGNMENT] += 0.25

        best_type = max(scores, key=lambda kind: scores[kind])
        best_score = scores[best_type]
        if best_score < 0.45:
            return Classification(LessonType.UNKNOWN, best_score, evidence, title=title)
        return Classification(best_type, min(best_score, 1.0), evidence, title=title)

    async def classify_page(self, page) -> Classification:
        url = page.url
        title = await page.title()
        html = await page.content()
        try:
            visible = await page.inner_text("body")
        except Exception:
            visible = ""
        heading = ""
        try:
            h1 = page.locator("h1")
            if await h1.count():
                heading = (await h1.first.inner_text()).strip()
        except Exception:
            heading = ""
        result = self.classify(url, html=html, visible_text=visible, title=heading or title)
        if heading:
            result.title = heading
        return result
