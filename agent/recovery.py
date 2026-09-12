from __future__ import annotations

import asyncio

from utils.helpers import backoff_seconds
from utils.logger import get_logger
from utils.screenshots import capture_debug_snapshot

log = get_logger("recovery")


class RecoveryExhausted(Exception):
    pass


class Recovery:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempts = 0

    def reset(self) -> None:
        self.attempts = 0

    async def wait(self) -> int:
        self.attempts += 1
        if self.attempts > self.max_retries:
            raise RecoveryExhausted(f"Exceeded {self.max_retries} retries")
        delay = backoff_seconds(self.attempts)
        log.warning("Recovery attempt %s, waiting %ss", self.attempts, delay)
        await asyncio.sleep(delay)
        return delay

    async def handle(self, page, reason: str, extra: dict | None = None) -> None:
        await capture_debug_snapshot(page, reason, extra)
        await self.wait()
