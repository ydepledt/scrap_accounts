from __future__ import annotations

from typing import Any

from scrap_common.browser import VisibleLinkScraper

from .models import ScrapeConfig
from .urls import INSTAGRAM_URL_RULES

INSTAGRAM_SCRAPER = VisibleLinkScraper(
    INSTAGRAM_URL_RULES,
    "Log in manually, then navigate to Likes, Saved, or a profile grid.",
)


def extract_visible_instagram_urls(page: Any) -> list[str]:
    return INSTAGRAM_SCRAPER.extract_visible_urls(page)


def scan_page_for_instagram_urls(page: Any, config: ScrapeConfig) -> list[str]:
    return INSTAGRAM_SCRAPER.scan_page(page, config)


def scrape_current_page_urls(
    page: Any,
    scrolls: int,
    scroll_delay_ms: int,
    scroll_pixels: int,
) -> list[str]:
    return scan_page_for_instagram_urls(
        page,
        ScrapeConfig(
            scrolls=scrolls,
            scroll_delay_ms=scroll_delay_ms,
            scroll_pixels=scroll_pixels,
            prompt_for_manual_navigation=False,
        ),
    )


def scrape_visible_urls(config: ScrapeConfig) -> list[str]:
    return INSTAGRAM_SCRAPER.scrape_visible_urls(config)
