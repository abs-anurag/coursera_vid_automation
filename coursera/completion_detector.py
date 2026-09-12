from __future__ import annotations

from browser.selectors import SELECTORS
from coursera.video_controller import VideoState


def is_video_complete(
    current_time: float,
    duration: float,
    ended: bool,
    playback_advanced: bool,
    threshold: float = 0.98,
    ui_complete: bool = False,
) -> bool:
    if not playback_advanced:
        return False
    if ended and (duration <= 0 or current_time >= max(duration * 0.9, current_time)):
        return True
    if duration > 1 and current_time >= duration * threshold:
        return True
    if ui_complete and duration > 1 and current_time >= duration * max(threshold, 0.95):
        return True
    return False


class CompletionDetector:
    def __init__(self, threshold: float = 0.98):
        self.threshold = threshold
        self._last_time = 0.0
        self._advanced = False
        self._samples = 0

    def reset(self) -> None:
        self._last_time = 0.0
        self._advanced = False
        self._samples = 0

    def observe(self, state: VideoState) -> None:
        self._samples += 1
        if state.currentTime > self._last_time + 0.4:
            self._advanced = True
        self._last_time = state.currentTime

    @property
    def playback_advanced(self) -> bool:
        return self._advanced

    def is_complete(self, state: VideoState, ui_complete: bool = False) -> bool:
        return is_video_complete(
            current_time=state.currentTime,
            duration=state.duration,
            ended=state.ended,
            playback_advanced=self._advanced,
            threshold=self.threshold,
            ui_complete=ui_complete,
        )

    async def ui_shows_complete(self, page) -> bool:
        for selector in SELECTORS.completed_markers:
            try:
                locator = page.locator(selector)
                if await locator.count():
                    return True
            except Exception:
                continue
        return False
