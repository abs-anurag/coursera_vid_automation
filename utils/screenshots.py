from __future__ import annotations

import json
from pathlib import Path

from config.settings import get_settings
from utils.helpers import now_stamp
from utils.logger import get_logger

log = get_logger("screenshots")


async def capture_debug_snapshot(page, reason: str, extra: dict | None = None) -> Path | None:
    settings = get_settings()
    if page is None:
        return None
    settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    safe_reason = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in reason)[:80]
    image_path = settings.screenshot_dir / f"{stamp}_{safe_reason}.png"
    info_path = settings.screenshot_dir / f"{stamp}_{safe_reason}.json"
    payload = extra or {}
    try:
        payload.update(
            {
                "url": page.url,
                "title": await page.title(),
            }
        )
        html_excerpt = await page.content()
        payload["html_excerpt"] = html_excerpt[:4000]
        await page.screenshot(path=str(image_path), full_page=False)
        info_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log.warning("Saved debug snapshot", extra={"url": page.url})
        return image_path
    except Exception as exc:
        log.error("Failed to capture screenshot: %s", exc)
        return None
