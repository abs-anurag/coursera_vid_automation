from __future__ import annotations

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from browser.selectors import SELECTORS
from utils.logger import get_logger

log = get_logger("page_manager")


class PageManager:
    def __init__(self, page: Page):
        self.page = page

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 60000) -> None:
        log.info("Navigating", extra={"url": url})
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)

    async def wait_for_idle(self, timeout: int = 15000) -> None:
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeoutError:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)

    async def visible_text(self, limit: int = 4000) -> str:
        try:
            text = await self.page.inner_text("body")
            return text[:limit]
        except Exception:
            return ""

    async def click_first(self, selectors: tuple[str, ...], timeout: int = 2500) -> bool:
        for selector in selectors:
            locator = self.page.locator(selector)
            try:
                if await locator.count() == 0:
                    continue
                target = locator.first
                if await target.is_visible(timeout=timeout):
                    await target.click(timeout=timeout)
                    log.info("Clicked selector %s", selector)
                    return True
            except Exception:
                continue
        return False

    async def dismiss_popups(self) -> None:
        await self.click_first(SELECTORS.popup_dismiss, timeout=1500)

    async def first_visible_text(self, selectors: tuple[str, ...]) -> str:
        for selector in selectors:
            locator = self.page.locator(selector)
            try:
                if await locator.count() == 0:
                    continue
                target = locator.first
                if await target.is_visible():
                    value = (await target.inner_text()).strip()
                    if value:
                        return value
            except Exception:
                continue
        return ""
