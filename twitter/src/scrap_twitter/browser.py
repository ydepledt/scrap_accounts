from __future__ import annotations

from typing import Any

from scrap_common.browser import VisibleLinkScraper

from .models import ScrapeConfig
from .urls import TWITTER_URL_RULES

TWITTER_SCRAPER = VisibleLinkScraper(
    TWITTER_URL_RULES,
    "Log in manually, then navigate to Home, Likes, Bookmarks, a profile, or a search timeline.",
)


def extract_visible_twitter_urls(page: Any) -> list[str]:
    return TWITTER_SCRAPER.extract_visible_urls(page)


def scan_page_for_twitter_urls(page: Any, config: ScrapeConfig) -> list[str]:
    return TWITTER_SCRAPER.scan_page(page, config)


def scrape_current_page_urls(
    page: Any,
    scrolls: int,
    scroll_delay_ms: int,
    scroll_pixels: int,
) -> list[str]:
    return scan_page_for_twitter_urls(
        page,
        ScrapeConfig(
            scrolls=scrolls,
            scroll_delay_ms=scroll_delay_ms,
            scroll_pixels=scroll_pixels,
            prompt_for_manual_navigation=False,
        ),
    )


def scrape_visible_urls(config: ScrapeConfig) -> list[str]:
    return TWITTER_SCRAPER.scrape_visible_urls(config)
