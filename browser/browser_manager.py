from __future__ import annotations

from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from browser.page_manager import PageManager
from config.settings import Settings
from utils.logger import get_logger

log = get_logger("browser_manager")

COURSERA_HOME = "https://www.coursera.org/"


class BrowserManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.page_manager: PageManager | None = None

    async def launch(self) -> Page:
        profile_dir = Path(self.settings.browser_profile_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        launch_args = {
            "user_data_dir": str(profile_dir),
            "headless": self.settings.headless,
            "viewport": {"width": 1440, "height": 900},
            "args": ["--disable-notifications"],
        }
        try:
            self.context = await self._playwright.chromium.launch_persistent_context(
                channel="chrome",
                **launch_args,
            )
            log.info("Launched Google Chrome with persistent profile")
        except Exception as exc:
            log.warning("Chrome channel unavailable (%s); falling back to Chromium", exc)
            self.context = await self._playwright.chromium.launch_persistent_context(**launch_args)
            log.info("Launched Chromium with persistent profile")

        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page_manager = PageManager(self.page)
        return self.page

    async def open_coursera(self, url: str | None = None) -> None:
        if not self.page_manager:
            raise RuntimeError("Browser is not launched")
        target = url or COURSERA_HOME
        await self.page_manager.goto(target)
        await self.page_manager.dismiss_popups()

    async def relaunch(self) -> Page:
        await self.close()
        return await self.launch()

    async def close(self) -> None:
        if self.context:
            try:
                await self.context.close()
            except Exception as exc:
                log.warning("Error closing browser context: %s", exc)
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as exc:
                log.warning("Error stopping Playwright: %s", exc)
        self.context = None
        self.page = None
        self.page_manager = None
        self._playwright = None
