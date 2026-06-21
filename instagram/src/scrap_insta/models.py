from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeAlias

from .constants import (
    COOKIE_BROWSER_CHOICES,
    DEFAULT_BROWSER_HEIGHT,
    DEFAULT_BROWSER_WIDTH,
    DEFAULT_MAX_IDLE_SCROLLS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROFILE_DIR,
    DEFAULT_RETRIES,
    DEFAULT_SCROLL_DELAY_MS,
    DEFAULT_SCROLL_PIXELS,
    DEFAULT_SCROLLS,
    INSTAGRAM_LOGIN_URL,
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ScrapeConfig:
    start_url: str = INSTAGRAM_LOGIN_URL
    profile_dir: Path = DEFAULT_PROFILE_DIR
    scrolls: int | None = DEFAULT_SCROLLS
    scroll_delay_ms: int = DEFAULT_SCROLL_DELAY_MS
    scroll_pixels: int = DEFAULT_SCROLL_PIXELS
    limit: int | None = None
    max_idle_scrolls: int = DEFAULT_MAX_IDLE_SCROLLS
    stop_when_no_new: bool = False
    headless: bool = False
    browser_width: int = DEFAULT_BROWSER_WIDTH
    browser_height: int = DEFAULT_BROWSER_HEIGHT
    prompt_for_manual_navigation: bool = True

    def validate(self) -> None:
        if self.scrolls is not None and self.scrolls < 0:
            raise ValueError("scrolls must be zero or greater.")
        if self.scrolls is None and not self.stop_when_no_new and self.limit is None:
            raise ValueError(
                "unlimited scrolling requires stop-when-no-new or limit."
            )
        if self.scroll_delay_ms < 0:
            raise ValueError("scroll-delay-ms must be zero or greater.")
        if self.scroll_pixels <= 0:
            raise ValueError("scroll-pixels must be greater than zero.")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be greater than zero when provided.")
        if self.max_idle_scrolls <= 0:
            raise ValueError("max-idle-scrolls must be greater than zero.")
        if self.browser_width <= 0 or self.browser_height <= 0:
            raise ValueError("browser dimensions must be greater than zero.")


@dataclass(frozen=True)
class DownloadConfig:
    urls: list[str]
    output_dir: Path = DEFAULT_OUTPUT_DIR
    cookies_from_browser: str | None = None
    cookies_file: Path | None = None
    archive_file: Path | None = None
    retries: int = DEFAULT_RETRIES
    skip_existing: bool = True
    dry_run: bool = False
    command: str = "download"
    source: str = "input"

    def validate(self) -> None:
        if self.retries < 0:
            raise ValueError("retries must be zero or greater.")
        if self.cookies_from_browser and self.cookies_file:
            raise ValueError("Use either cookies-from-browser or cookies-file, not both.")
        if (
            self.cookies_from_browser is not None
            and self.cookies_from_browser not in COOKIE_BROWSER_CHOICES
        ):
            choices = ", ".join(COOKIE_BROWSER_CHOICES)
            raise ValueError(f"Unsupported browser for cookies: {self.cookies_from_browser}. Choices: {choices}.")
        if self.cookies_file is not None and not self.cookies_file.exists():
            raise FileNotFoundError(f"Cookies file not found: {self.cookies_file}")


@dataclass(frozen=True)
class DownloadItemResult:
    url: str
    source: str
    status: str
    output_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "url": self.url,
            "source": self.source,
            "status": self.status,
            "output_path": self.output_path,
            "error": self.error,
        }


@dataclass
class RunReport:
    command: str
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    items: list[DownloadItemResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self) -> "RunReport":
        self.finished_at = utc_now_iso()
        return self

    @property
    def total_urls(self) -> int:
        return len(self.items)

    @property
    def failed_count(self) -> int:
        return self.status_counts().get("failed", 0)

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.status] = counts.get(item.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_urls": self.total_urls,
            "status_counts": self.status_counts(),
            "metadata": self.metadata,
            "items": [item.to_dict() for item in self.items],
        }


DownloadReport: TypeAlias = RunReport
