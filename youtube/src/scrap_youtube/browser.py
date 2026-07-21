from __future__ import annotations

from typing import Any

from scrap_common.browser import VisibleLinkScraper

from .models import ScrapeConfig
from .urls import YOUTUBE_URL_RULES

YOUTUBE_SCRAPER = VisibleLinkScraper(
    YOUTUBE_URL_RULES,
    "Log in manually, then navigate to History, Liked videos, Playlists, or a channel.",
)


def extract_visible_youtube_urls(page: Any) -> list[str]:
    return YOUTUBE_SCRAPER.extract_visible_urls(page)


def scan_page_for_youtube_urls(page: Any, config: ScrapeConfig) -> list[str]:
    return YOUTUBE_SCRAPER.scan_page(page, config)


def scrape_current_page_urls(
    page: Any,
    scrolls: int,
    scroll_delay_ms: int,
    scroll_pixels: int,
) -> list[str]:
    return scan_page_for_youtube_urls(
        page,
        ScrapeConfig(
            scrolls=scrolls,
            scroll_delay_ms=scroll_delay_ms,
            scroll_pixels=scroll_pixels,
            prompt_for_manual_navigation=False,
        ),
    )


def scrape_visible_urls(config: ScrapeConfig) -> list[str]:
    return YOUTUBE_SCRAPER.scrape_visible_urls(config)
