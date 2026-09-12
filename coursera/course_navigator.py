from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from browser.selectors import SELECTORS
from coursera.course_detector import CourseDetector
from coursera.lesson_detector import LessonDetector, LessonType
from database.database import Database
from database.models import LessonStatus
from utils.logger import get_logger

log = get_logger("course_navigator")


@dataclass
class OutlineItem:
    title: str
    url: str
    lesson_type: LessonType
    completed: bool = False


class CourseNavigator:
    def __init__(self, page, course_detector: CourseDetector, lesson_detector: LessonDetector, database: Database):
        self.page = page
        self.course_detector = course_detector
        self.lesson_detector = lesson_detector
        self.database = database
        self.items: list[OutlineItem] = []

    def _same_course(self, href: str, course_slug: str) -> bool:
        slug = self.course_detector.slug(href)
        return bool(slug) and slug == course_slug

    async def scan_course(self, course_slug: str) -> list[OutlineItem]:
        items: list[OutlineItem] = []
        seen: set[str] = set()
        for selector in SELECTORS.course_nav_links:
            locator = self.page.locator(selector)
            try:
                count = await locator.count()
            except Exception:
                continue
            for index in range(count):
                link = locator.nth(index)
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    url = urljoin(self.page.url, href).split("?")[0]
                    if url in seen:
                        continue
                    if not SELECTORS.item_link_pattern.search(urlparse(url).path):
                        continue
                    if not self._same_course(url, course_slug):
                        continue
                    seen.add(url)
                    title = (await link.inner_text() or "").strip() or url
                    classification = self.lesson_detector.classify(url, visible_text=title, title=title)
                    completed = False
                    try:
                        aria = await link.get_attribute("aria-label") or ""
                        completed = "complete" in aria.lower()
                    except Exception:
                        completed = False
                    stored = self.database.get_lesson(url)
                    if stored and stored.status in {LessonStatus.COMPLETED, LessonStatus.SKIPPED}:
                        completed = True
                    items.append(
                        OutlineItem(
                            title=title.split("\n")[0].strip(),
                            url=url,
                            lesson_type=classification.lesson_type,
                            completed=completed,
                        )
                    )
                except Exception:
                    continue
        self.items = items
        log.info("Scanned %s outline items", len(items))
        return items

    def get_next_video(self) -> OutlineItem | None:
        for item in self.items:
            if item.lesson_type == LessonType.VIDEO and not item.completed:
                stored = self.database.get_lesson(item.url)
                if stored and stored.status == LessonStatus.COMPLETED:
                    continue
                return item
        return None

    def get_next_item(self, current_url: str) -> OutlineItem | None:
        urls = [item.url for item in self.items]
        try:
            index = urls.index(current_url.split("?")[0])
        except ValueError:
            return self.get_next_video()
        for item in self.items[index + 1 :]:
            stored = self.database.get_lesson(item.url)
            if stored and stored.status in {LessonStatus.COMPLETED, LessonStatus.SKIPPED}:
                continue
            if item.completed and item.lesson_type != LessonType.VIDEO:
                continue
            if item.lesson_type == LessonType.VIDEO and item.completed:
                continue
            return item
        return self.get_next_video()

    async def open_lesson(self, item: OutlineItem, expected_slug: str | None = None) -> None:
        slug = self.course_detector.slug(item.url)
        if expected_slug and slug != expected_slug:
            raise RuntimeError("Refusing to open a lesson outside the target course")
        log.info("Opening lesson: %s", item.title, extra={"lesson": item.title, "url": item.url})
        await self.page.goto(item.url, wait_until="domcontentloaded", timeout=60000)

    async def move_to_next_lesson(self, current_url: str, course_slug: str) -> OutlineItem | None:
        if not self.items:
            await self.scan_course(course_slug)
        nxt = self.get_next_item(current_url)
        if nxt is None:
            nxt = self.get_next_video()
        if nxt is None:
            return None
        await self.open_lesson(nxt, course_slug)
        return nxt
