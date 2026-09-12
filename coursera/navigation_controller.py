from __future__ import annotations

from browser.page_manager import PageManager
from browser.selectors import SELECTORS
from coursera.course_detector import CourseDetector
from coursera.lesson_detector import LessonType
from utils.logger import get_logger

log = get_logger("navigation_controller")


class NavigationController:
    def __init__(self, page, page_manager: PageManager, course_detector: CourseDetector):
        self.page = page
        self.page_manager = page_manager
        self.course_detector = course_detector

    async def assert_target_course(self, expected_slug: str) -> bool:
        actual = self.course_detector.slug(self.page.url)
        if actual and expected_slug and actual != expected_slug:
            log.warning(
                "Left target course (expected %s, found %s); returning",
                expected_slug,
                actual,
            )
            await self.page.goto(f"https://www.coursera.org/learn/{expected_slug}", wait_until="domcontentloaded")
            return False
        return True

    async def skip_non_video(self, lesson_type: LessonType, expected_slug: str) -> bool:
        log.info("%s detected - skipping without interacting with answers", lesson_type.value)
        clicked = await self.page_manager.click_first(SELECTORS.next_buttons, timeout=2000)
        if clicked:
            await self.page_manager.wait_for_idle(timeout=8000)
            return await self.assert_target_course(expected_slug)
        course_home = f"https://www.coursera.org/learn/{expected_slug}"
        await self.page.goto(course_home, wait_until="domcontentloaded")
        return True
