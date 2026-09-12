from __future__ import annotations

import asyncio
import time

from ai.vision_classifier import VisionClassifier
from agent.decision_engine import DecisionEngine
from agent.recovery import Recovery, RecoveryExhausted
from agent.state import AgentState, InvalidTransition, RuntimeContext, transition
from browser.browser_manager import BrowserManager
from config.settings import Settings
from coursera.completion_detector import CompletionDetector
from coursera.course_detector import CourseDetector
from coursera.course_navigator import CourseNavigator, OutlineItem
from coursera.lesson_detector import Classification, LessonDetector, LessonType
from coursera.navigation_controller import NavigationController
from coursera.video_controller import VideoController
from database.database import Database
from database.models import ControlCommand, LessonRecord, LessonStatus
from utils.helpers import format_elapsed, utc_now_iso
from utils.logger import get_logger
from utils.screenshots import capture_debug_snapshot

log = get_logger("agent")


class CourseraVideoAgent:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.browser = BrowserManager(settings)
        self.course_detector = CourseDetector(settings)
        self.lesson_detector = LessonDetector()
        self.decision_engine = DecisionEngine()
        self.completion = CompletionDetector(settings.video_complete_threshold)
        self.recovery = Recovery(settings.max_retries)
        self.state = AgentState.STARTING
        self.ctx = RuntimeContext()
        self._paused_from: AgentState | None = None
        self._stop = False
        self._continue_login = asyncio.Event()
        self.started_at = time.monotonic()

    def set_state(self, target: AgentState) -> None:
        try:
            self.state = transition(self.state, target)
        except InvalidTransition:
            if target in {AgentState.STOPPED, AgentState.PAUSED, AgentState.ERROR}:
                self.state = target
            else:
                log.warning("Rejected transition %s -> %s", self.state.value, target.value)
                return
        self.database.update_runtime(agent_state=self.state.value)
        self.database.add_event(f"State: {self.state.value}")

    async def run(self) -> None:
        if not self.settings.target_course_configured:
            message = (
                "A target course is required. Set COURSE_NAME and/or COURSE_URL "
                "in .env, or pass --course-name / --course."
            )
            log.error(message)
            self.database.add_event(message, "ERROR")
            self.state = AgentState.STOPPED
            return

        self.started_at = time.monotonic()
        self.set_state(AgentState.STARTING)
        page = await self.browser.launch()
        start_url = self.settings.course_url.strip() or "https://www.coursera.org/"
        await self.browser.open_coursera(start_url)
        await self.browser.page_manager.dismiss_popups()

        try:
            await self._wait_for_login(page)
            await self._wait_for_target_course(page)
            await self._main_loop(page)
        except asyncio.CancelledError:
            self.set_state(AgentState.STOPPED)
        except Exception as exc:
            log.exception("Agent crashed: %s", exc)
            await capture_debug_snapshot(page, "agent_crash", {"error": str(exc)})
            self.set_state(AgentState.ERROR)
            self.set_state(AgentState.STOPPED)
        finally:
            self.database.update_runtime(agent_state=AgentState.STOPPED.value)
            await self.browser.close()

    async def _handle_control(self) -> bool:
        command = self.database.pop_command()
        if command == ControlCommand.STOP:
            self._stop = True
            self.set_state(AgentState.STOPPED)
            return True
        if command == ControlCommand.PAUSE:
            if self.state != AgentState.PAUSED:
                self._paused_from = self.state
                self.set_state(AgentState.PAUSED)
                self.database.add_event("Paused by user")
        if command == ControlCommand.RESUME and self.state == AgentState.PAUSED:
            resume_to = self._paused_from or AgentState.DETECTING_LESSON
            self._paused_from = None
            self.state = AgentState.PAUSED
            self.set_state(resume_to)
            self.database.add_event("Resumed by user")
        if command == ControlCommand.CONTINUE:
            self._continue_login.set()
        while self.state == AgentState.PAUSED and not self._stop:
            await asyncio.sleep(0.5)
            nxt = self.database.pop_command()
            if nxt == ControlCommand.STOP:
                self._stop = True
                self.set_state(AgentState.STOPPED)
                return True
            if nxt == ControlCommand.RESUME:
                resume_to = self._paused_from or AgentState.DETECTING_LESSON
                self._paused_from = None
                self.set_state(resume_to)
                break
            if nxt == ControlCommand.CONTINUE:
                self._continue_login.set()
        return self._stop

    async def _wait_for_login(self, page) -> None:
        url = page.url
        text = await self.browser.page_manager.visible_text()
        needs_login = self.course_detector.is_login_url(url) or (
            "log in" in text.lower() and "learn/" not in url
        )
        if not needs_login:
            return
        self.set_state(AgentState.WAITING_FOR_LOGIN)
        message = "Please log in manually. Press Continue when ready."
        print(f"\n{message}\nDashboard: http://{self.settings.dashboard_host}:{self.settings.dashboard_port}\n")
        self.database.add_event(message)
        self._continue_login.clear()
        deadline = time.monotonic() + self.settings.login_wait_timeout_seconds
        while time.monotonic() < deadline and not self._stop:
            if await self._handle_control():
                return
            if self._continue_login.is_set():
                break
            if not self.course_detector.is_login_url(page.url) and "learn/" in page.url:
                break
            await asyncio.sleep(1.5)
        await self.browser.page_manager.dismiss_popups()

    async def _wait_for_target_course(self, page) -> None:
        self.set_state(AgentState.WAITING_FOR_COURSE)
        expected = self.settings.course_name or self.settings.course_url
        self.database.add_event(f"Waiting for target course: {expected}")
        print(
            f"\nOpen only this course: {expected}\n"
            "The agent will not process any other course.\n"
            "Press Continue in the dashboard when the course is open.\n"
        )
        if self.settings.course_url.strip():
            await self.browser.page_manager.goto(self.settings.course_url.strip())

        deadline = time.monotonic() + self.settings.course_wait_timeout_seconds
        while time.monotonic() < deadline and not self._stop:
            if await self._handle_control():
                return
            detected = await self.course_detector.detect(page, self.browser.page_manager)
            if detected and detected.matches_target:
                self.ctx.course_name = detected.name
                self.ctx.course_url = detected.url
                self.ctx.course_slug = detected.slug
                self.database.update_runtime(course=detected.name, course_url=detected.url)
                self.database.add_event(f"Locked onto course: {detected.name}")
                return
            if detected and not detected.matches_target:
                log.warning(
                    "Ignoring course '%s' because it is not the configured target",
                    detected.name,
                )
            await asyncio.sleep(2)
        raise RuntimeError("Timed out waiting for the named target course")

    async def _main_loop(self, page) -> None:
        navigator = CourseNavigator(page, self.course_detector, self.lesson_detector, self.database)
        navigation = NavigationController(page, self.browser.page_manager, self.course_detector)
        self.set_state(AgentState.SCANNING_COURSE)
        await navigator.scan_course(self.ctx.course_slug)
        self._persist_outline(navigator.items)
        nxt = navigator.get_next_video()
        if nxt is None:
            self.set_state(AgentState.COURSE_COMPLETE)
            self.set_state(AgentState.STOPPED)
            return
        await navigator.open_lesson(nxt, self.ctx.course_slug)

        while not self._stop:
            if await self._handle_control():
                return
            if not await navigation.assert_target_course(self.ctx.course_slug):
                await navigator.scan_course(self.ctx.course_slug)
                video = navigator.get_next_video()
                if video:
                    await navigator.open_lesson(video, self.ctx.course_slug)
                continue

            self.set_state(AgentState.DETECTING_LESSON)
            classification = await self._classify(page)
            if classification.lesson_type == LessonType.UNKNOWN or not classification.is_confident:
                await capture_debug_snapshot(page, "unknown_page", {"evidence": classification.evidence})
                try:
                    await self.recovery.handle(page, "unknown_page")
                    continue
                except RecoveryExhausted:
                    self.database.add_event("Unable to determine lesson type; pausing", "ERROR")
                    self.set_state(AgentState.PAUSED)
                    continue

            decided = self.decision_engine.decide(classification, self.state)
            self.ctx.lesson_title = classification.title or page.url
            self.ctx.lesson_type = classification.lesson_type.value
            self._sync_runtime()

            try:
                if decided == AgentState.OPENING_VIDEO:
                    await self._play_until_complete(page)
                    self.recovery.reset()
                elif decided == AgentState.SKIPPING_QUIZ:
                    self.set_state(AgentState.SKIPPING_QUIZ)
                    self._mark_current(classification, LessonStatus.SKIPPED)
                    self.database.add_event("Quiz detected - skipping")
                    await navigation.skip_non_video(LessonType.QUIZ, self.ctx.course_slug)
                elif decided == AgentState.SKIPPING_READING:
                    self.set_state(AgentState.SKIPPING_READING)
                    self._mark_current(classification, LessonStatus.SKIPPED)
                    self.database.add_event("Reading detected - skipping")
                    await navigation.skip_non_video(LessonType.READING, self.ctx.course_slug)
                elif decided == AgentState.SKIPPING_ASSIGNMENT:
                    self.set_state(AgentState.SKIPPING_ASSIGNMENT)
                    self._mark_current(classification, LessonStatus.SKIPPED)
                    self.database.add_event("Assignment detected - skipping")
                    await navigation.skip_non_video(LessonType.ASSIGNMENT, self.ctx.course_slug)
                else:
                    await capture_debug_snapshot(page, "undecided")
                    self.set_state(AgentState.PAUSED)
                    continue
            except (RuntimeError, RecoveryExhausted) as exc:
                log.error("Action failed: %s", exc)
                await capture_debug_snapshot(page, "action_failed", {"error": str(exc)})
                self.set_state(AgentState.PAUSED)
                continue

            self.set_state(AgentState.MOVING_TO_NEXT)
            await navigator.scan_course(self.ctx.course_slug)
            self._persist_outline(navigator.items)
            following = navigator.get_next_item(page.url) or navigator.get_next_video()
            if following is None:
                self.database.add_event("No more videos to process")
                self.set_state(AgentState.COURSE_COMPLETE)
                self.set_state(AgentState.STOPPED)
                return
            await navigator.open_lesson(following, self.ctx.course_slug)

    async def _classify(self, page) -> Classification:
        result = await self.lesson_detector.classify_page(page)
        if result.is_confident:
            self.database.add_event(f"Lesson detected: {result.lesson_type.value}")
            return result
        if self.settings.ai_enabled and self.settings.ai_api_key:
            screenshot = await page.screenshot(type="png")
            vision = VisionClassifier(
                self.settings.ai_api_key,
                self.settings.ai_model,
                self.settings.ai_base_url,
            )
            guessed = await vision.classify_image(screenshot)
            if guessed != LessonType.UNKNOWN:
                result.lesson_type = guessed
                result.confidence = 0.65
                result.evidence.append("vision")
                self.database.add_event(f"Vision classified page as {guessed.value}")
        return result

    async def _play_until_complete(self, page) -> None:
        video = VideoController(page)
        if not await video.is_video_page():
            raise RuntimeError("Expected a video page but no player was found")
        self.set_state(AgentState.OPENING_VIDEO)
        self._mark_current_playing()
        await video.play_video()
        self.set_state(AgentState.PLAYING_VIDEO)
        self.database.add_event("Video started")
        self.completion.reset()
        stall_started: float | None = None
        last_time = 0.0

        while not self._stop:
            if await self._handle_control():
                return
            if self.state == AgentState.PAUSED:
                continue
            state = await video.get_state()
            self.completion.observe(state)
            if state.duration > 0:
                percent = int((state.currentTime / state.duration) * 100)
                log.info("Video progress: %s%%", percent, extra={"percent": percent, "lesson": self.ctx.lesson_title})
            if state.paused:
                await video.play_video()
            if state.currentTime <= last_time + 0.2:
                stall_started = stall_started or time.monotonic()
                if time.monotonic() - stall_started > self.settings.stall_timeout_seconds:
                    log.warning("Video playback stalled")
                    await self.recovery.handle(page, "video_stalled")
                    await video.play_video()
                    stall_started = None
            else:
                stall_started = None
            last_time = state.currentTime

            ui_complete = await self.completion.ui_shows_complete(page)
            if self.completion.is_complete(state, ui_complete=ui_complete):
                self.set_state(AgentState.VERIFYING_COMPLETION)
                verify = await video.get_state()
                if self.completion.is_complete(verify, ui_complete=ui_complete):
                    self._mark_current_completed()
                    self.database.add_event("Video completed")
                    self.recovery.reset()
                    return
            await asyncio.sleep(self.settings.playback_poll_seconds)

    def _mark_current_playing(self) -> None:
        self.database.upsert_lesson(
            LessonRecord(
                course=self.ctx.course_name,
                course_url=self.ctx.course_url,
                lesson=self.ctx.lesson_title,
                lesson_url=self.browser.page.url if self.browser.page else "",
                lesson_type="VIDEO",
                status=LessonStatus.PLAYING,
                started_at=utc_now_iso(),
            )
        )

    def _mark_current_completed(self) -> None:
        self.database.upsert_lesson(
            LessonRecord(
                course=self.ctx.course_name,
                course_url=self.ctx.course_url,
                lesson=self.ctx.lesson_title,
                lesson_url=self.browser.page.url if self.browser.page else "",
                lesson_type="VIDEO",
                status=LessonStatus.COMPLETED,
                completed_at=utc_now_iso(),
            )
        )
        self._sync_runtime()

    def _mark_current(self, classification: Classification, status: LessonStatus) -> None:
        self.database.upsert_lesson(
            LessonRecord(
                course=self.ctx.course_name,
                course_url=self.ctx.course_url,
                lesson=classification.title or self.ctx.lesson_title,
                lesson_url=self.browser.page.url if self.browser.page else "",
                lesson_type=classification.lesson_type.value,
                status=status,
                completed_at=utc_now_iso() if status == LessonStatus.SKIPPED else None,
            )
        )

    def _persist_outline(self, items: list[OutlineItem]) -> None:
        for item in items:
            existing = self.database.get_lesson(item.url)
            status = existing.status if existing else LessonStatus.PENDING
            if item.completed and item.lesson_type == LessonType.VIDEO and status != LessonStatus.COMPLETED:
                status = LessonStatus.COMPLETED
            self.database.upsert_lesson(
                LessonRecord(
                    course=self.ctx.course_name,
                    course_url=self.ctx.course_url,
                    lesson=item.title,
                    lesson_url=item.url,
                    lesson_type=item.lesson_type.value,
                    status=status,
                )
            )
        completed, total = self.database.video_counts(self.ctx.course_url)
        self.database.update_runtime(videos_completed=completed, videos_total=total)
        self._sync_runtime()

    def _sync_runtime(self) -> None:
        completed, total = self.database.video_counts(self.ctx.course_url) if self.ctx.course_url else (0, 0)
        self.database.update_runtime(
            course=self.ctx.course_name,
            course_url=self.ctx.course_url,
            current_lesson=self.ctx.lesson_title,
            current_type=self.ctx.lesson_type,
            agent_state=self.state.value,
            videos_completed=completed,
            videos_total=total,
            elapsed_seconds=time.monotonic() - self.started_at,
        )
