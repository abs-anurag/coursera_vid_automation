from __future__ import annotations

from dataclasses import dataclass

from browser.page_manager import PageManager
from browser.selectors import SELECTORS
from config.settings import Settings
from utils.helpers import names_match, slug_from_url
from utils.logger import get_logger

log = get_logger("course_detector")


@dataclass
class DetectedCourse:
    name: str
    url: str
    slug: str
    matches_target: bool


class CourseDetector:
    def __init__(self, settings: Settings):
        self.settings = settings

    def parse_url(self, url: str) -> str:
        match = SELECTORS.course_url_pattern.search(url or "")
        return match.group(0).split("?")[0] if match else ""

    def slug(self, url: str) -> str:
        return slug_from_url(url)

    def matches_target(self, name: str, url: str) -> bool:
        expected_name = self.settings.course_name.strip()
        expected_url = self.settings.course_url.strip()
        if not expected_name and not expected_url:
            return False
        actual_slug = self.slug(url)
        if expected_url:
            expected_slug = self.slug(expected_url)
            if expected_slug and actual_slug and expected_slug != actual_slug:
                return False
            if expected_slug and actual_slug and expected_slug == actual_slug and not expected_name:
                return True
        if expected_name:
            if names_match(expected_name, name):
                return True
            if actual_slug and names_match(expected_name.replace(" ", "-"), actual_slug.replace("-", " ")):
                return True
            if actual_slug and expected_name.lower().replace(" ", "-") in actual_slug:
                return True
            return False
        return bool(actual_slug)

    async def detect(self, page, page_manager: PageManager | None = None) -> DetectedCourse | None:
        url = page.url
        course_url = self.parse_url(url)
        if not course_url:
            return None
        slug = self.slug(course_url)
        name = ""
        if page_manager:
            name = await page_manager.first_visible_text(SELECTORS.course_title)
        if not name:
            try:
                name = await page.title()
            except Exception:
                name = slug
        name = name.replace(" | Coursera", "").strip() or slug.replace("-", " ").title()
        detected = DetectedCourse(
            name=name,
            url=f"https://www.coursera.org/learn/{slug}",
            slug=slug,
            matches_target=self.matches_target(name, course_url),
        )
        log.info("Course detected: %s", detected.name, extra={"course": detected.name, "url": detected.url})
        return detected

    def is_login_url(self, url: str) -> bool:
        return any(pattern.search(url or "") for pattern in SELECTORS.login_url_patterns)
