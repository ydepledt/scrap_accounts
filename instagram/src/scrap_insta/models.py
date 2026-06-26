from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeAlias

from .config import CONFIG


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ScrapeConfig:
    start_url: str = CONFIG.instagram_login_url
    profile_dir: Path = CONFIG.profile_dir
    scrolls: int | None = CONFIG.scrolls
    scroll_delay_ms: int = CONFIG.scroll_delay_ms
    scroll_pixels: int = CONFIG.scroll_pixels
    limit: int | None = None
    max_idle_scrolls: int = CONFIG.max_idle_scrolls
    stop_when_no_new: bool = False
    headless: bool = False
    browser_width: int = CONFIG.browser_width
    browser_height: int = CONFIG.browser_height
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
    output_dir: Path = CONFIG.output_dir
    cookies_from_browser: str | None = None
    cookies_file: Path | None = None
    archive_file: Path | None = None
    retries: int = CONFIG.retries
    comments_limit: int = CONFIG.comments_limit
    format_selector: str | None = CONFIG.format_selector
    audio_only: bool = CONFIG.audio_only
    write_thumbnail: bool = CONFIG.write_thumbnail
    metadata_only: bool = CONFIG.metadata_only
    skip_existing: bool = True
    dry_run: bool = False
    command: str = "download"
    source: str = "input"

    def validate(self) -> None:
        if self.retries < 0:
            raise ValueError("retries must be zero or greater.")
        if self.comments_limit < 0:
            raise ValueError("comments-limit must be zero or greater.")
        if self.cookies_from_browser and self.cookies_file:
            raise ValueError("Use either cookies-from-browser or cookies-file, not both.")
        if (
            self.cookies_from_browser is not None
            and self.cookies_from_browser not in CONFIG.cookie_browser_choices
        ):
            choices = ", ".join(CONFIG.cookie_browser_choices)
            raise ValueError(
                f"Unsupported browser for cookies: {self.cookies_from_browser}. "
                f"Choices: {choices}."
            )
        if self.cookies_file is not None and not self.cookies_file.exists():
            raise FileNotFoundError(f"Cookies file not found: {self.cookies_file}")


@dataclass(frozen=True)
class DownloadItemResult:
    url: str
    source: str
    status: str
    output_path: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    error_type: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source": self.source,
            "status": self.status,
            "output_path": self.output_path,
            "description": self.description,
            "tags": self.tags,
            "comments": self.comments,
            "error_type": self.error_type,
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
