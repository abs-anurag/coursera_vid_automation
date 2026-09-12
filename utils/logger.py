from __future__ import annotations

import logging
import sys
from pathlib import Path

from config.settings import PROJECT_ROOT, get_settings

_CONFIGURED = False


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras = []
        for key in ("course", "lesson", "percent", "state", "url"):
            value = getattr(record, key, None)
            if value not in (None, ""):
                extras.append(f"{key}={value}")
        if extras:
            return f"{base} | {' '.join(extras)}"
        return base


def setup_logging(level: str | None = None) -> None:
    global _CONFIGURED
    settings = get_settings()
    log_level = (level or settings.log_level).upper()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "agent.log"

    root = logging.getLogger("coursera_agent")
    root.setLevel(log_level)
    root.handlers.clear()

    formatter = StructuredFormatter("%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    if not _CONFIGURED:
        setup_logging()
    return logging.getLogger(f"coursera_agent.{name}")


def project_root() -> Path:
    return PROJECT_ROOT
