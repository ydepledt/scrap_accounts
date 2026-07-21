from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from scrap_common.models import DownloadItemResult, RunReport

from .config import CONFIG


@dataclass(frozen=True)
class ScrapeConfig:
    start_url: str = CONFIG.youtube_start_url
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
            raise ValueError("unlimited scrolling requires stop-when-no-new or limit.")
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
    cookie_browser_choices: tuple[str, ...] = CONFIG.cookie_browser_choices
    archive_file: Path | None = None
    retries: int = CONFIG.retries
    comments_limit: int = CONFIG.comments_limit
    format_selector: str | None = CONFIG.format_selector
    audio_only: bool = CONFIG.audio_only
    write_thumbnail: bool = CONFIG.write_thumbnail
    metadata_only: bool = CONFIG.metadata_only
    include_playlists: bool = CONFIG.include_playlists
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
            and self.cookies_from_browser not in self.cookie_browser_choices
        ):
            choices = ", ".join(self.cookie_browser_choices)
            raise ValueError(
                f"Unsupported browser for cookies: {self.cookies_from_browser}. "
                f"Choices: {choices}."
            )
        if self.cookies_file is not None and not self.cookies_file.exists():
            raise FileNotFoundError(f"Cookies file not found: {self.cookies_file}")


DownloadReport: TypeAlias = RunReport
