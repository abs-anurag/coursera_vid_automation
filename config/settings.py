from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_path(value: Path | str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    browser_profile_dir: Path = Field(default=PROJECT_ROOT / "chrome_profile")
    headless: bool = False
    course_url: str = ""
    course_name: str = ""
    log_level: str = "INFO"
    screenshot_on_error: bool = True

    ai_enabled: bool = False
    ai_api_key: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"

    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8765
    video_complete_threshold: float = 0.98
    stall_timeout_seconds: float = 45.0
    max_retries: int = 3
    playback_poll_seconds: float = 5.0
    login_wait_timeout_seconds: float = 1800.0
    course_wait_timeout_seconds: float = 1800.0

    database_path: Path = Field(default=PROJECT_ROOT / "data" / "progress.db")
    screenshot_dir: Path = Field(default=PROJECT_ROOT / "logs" / "screenshots")
    log_dir: Path = Field(default=PROJECT_ROOT / "logs")

    @field_validator(
        "browser_profile_dir",
        "database_path",
        "screenshot_dir",
        "log_dir",
        mode="before",
    )
    @classmethod
    def resolve_paths(cls, value: Path | str) -> Path:
        return _resolve_path(value)

    @property
    def target_course_configured(self) -> bool:
        return bool(self.course_name.strip() or self.course_url.strip())

    def ensure_directories(self) -> None:
        self.browser_profile_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
