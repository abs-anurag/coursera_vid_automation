from __future__ import annotations

from dataclasses import dataclass

from browser.selectors import SELECTORS
from utils.logger import get_logger

log = get_logger("video_controller")

VIDEO_STATE_SCRIPT = """
() => {
  const videos = Array.from(document.querySelectorAll('video'));
  const video = videos.find(v => v.offsetParent !== null || v.readyState > 0) || videos[0];
  if (!video) {
    return { present: false, currentTime: 0, duration: 0, ended: false, paused: true, readyState: 0 };
  }
  const duration = Number.isFinite(video.duration) ? video.duration : 0;
  return {
    present: true,
    currentTime: video.currentTime || 0,
    duration: duration || 0,
    ended: Boolean(video.ended),
    paused: Boolean(video.paused),
    readyState: video.readyState || 0
  };
}
"""


@dataclass
class VideoState:
    present: bool = False
    currentTime: float = 0.0
    duration: float = 0.0
    ended: bool = False
    paused: bool = True
    readyState: int = 0


class VideoController:
    def __init__(self, page):
        self.page = page

    async def is_video_page(self) -> bool:
        state = await self.get_state()
        if state.present:
            return True
        for selector in SELECTORS.video_containers:
            try:
                if await self.page.locator(selector).count():
                    return True
            except Exception:
                continue
        return False

    async def get_state(self) -> VideoState:
        try:
            data = await self.page.evaluate(VIDEO_STATE_SCRIPT)
            return VideoState(**data)
        except Exception as exc:
            log.warning("Unable to read video state: %s", exc)
            return VideoState()

    async def get_current_time(self) -> float:
        return (await self.get_state()).currentTime

    async def get_duration(self) -> float:
        return (await self.get_state()).duration

    async def is_finished(self) -> bool:
        state = await self.get_state()
        if state.ended:
            return True
        if state.duration > 0 and state.currentTime >= state.duration * 0.995:
            return True
        return False

    async def play_video(self) -> None:
        state = await self.get_state()
        if state.present and not state.paused:
            log.info("Video already playing")
            return
        for selector in SELECTORS.play_buttons:
            locator = self.page.locator(selector)
            try:
                if await locator.count() == 0:
                    continue
                button = locator.first
                if await button.is_visible():
                    await button.click(timeout=3000)
                    log.info("Clicked play control")
                    return
            except Exception:
                continue
        await self.page.evaluate(
            """
            () => {
              const video = document.querySelector('video');
              if (video && video.paused) {
                return video.play().then(() => true).catch(() => false);
              }
              return false;
            }
            """
        )
        log.info("Requested video.play() on media element")
