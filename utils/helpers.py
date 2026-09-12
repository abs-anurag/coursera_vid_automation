from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def names_match(expected: str, actual: str) -> bool:
    exp = normalize_text(expected)
    act = normalize_text(actual)
    if not exp or not act:
        return False
    return exp in act or act in exp


def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    match = re.search(r"/learn/([^/]+)", path)
    return match.group(1) if match else ""


def slug_from_name(name: str) -> str:
    slug = normalize_text(name)
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


def backoff_seconds(attempt: int) -> int:
    schedule = [2, 5, 10]
    if attempt <= 0:
        return schedule[0]
    index = min(attempt - 1, len(schedule) - 1)
    return schedule[index]


def format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
