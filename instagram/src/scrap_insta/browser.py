from __future__ import annotations

import logging
from itertools import count
from typing import Any

from .models import ScrapeConfig
from .urls import normalize_instagram_url

LOGGER = logging.getLogger(__name__)


def extract_visible_instagram_urls(page: Any) -> list[str]:
    raw_urls = page.evaluate(
        """
        () => Array.from(document.querySelectorAll('a[href]'))
            .map((anchor) => anchor.href)
            .filter((href) => (
                href.includes('/reel/')
                || href.includes('/p/')
                || href.includes('/tv/')
            ))
        """
    )

    normalized_urls = {
        normalized_url
        for raw_url in raw_urls
        if isinstance(raw_url, str)
        if (normalized_url := normalize_instagram_url(raw_url)) is not None
    }
    return sorted(normalized_urls)


def scan_page_for_instagram_urls(page: Any, config: ScrapeConfig) -> list[str]:
    config.validate()
    collected_urls: set[str] = set(extract_visible_instagram_urls(page))
    idle_scrolls = 0

    LOGGER.info("Initial URLs found: %s", len(collected_urls))
    if config.limit is not None and len(collected_urls) >= config.limit:
        return sorted(collected_urls)[: config.limit]

    scroll_indexes = count(1) if config.scrolls is None else range(1, config.scrolls + 1)
    scroll_total = "unlimited" if config.scrolls is None else str(config.scrolls)

    for scroll_index in scroll_indexes:
        before_count = len(collected_urls)
        page.mouse.wheel(0, config.scroll_pixels)
        page.wait_for_timeout(config.scroll_delay_ms)
        collected_urls.update(extract_visible_instagram_urls(page))
        new_count = len(collected_urls) - before_count

        LOGGER.info(
            "Scroll %s/%s - total URLs: %s (+%s)",
            scroll_index,
            scroll_total,
            len(collected_urls),
            new_count,
        )

        if config.limit is not None and len(collected_urls) >= config.limit:
            return sorted(collected_urls)[: config.limit]

        idle_scrolls = idle_scrolls + 1 if new_count == 0 else 0
        if config.stop_when_no_new and idle_scrolls >= config.max_idle_scrolls:
            LOGGER.info("Stopping after %s idle scroll(s).", idle_scrolls)
            break

    return sorted(collected_urls)


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
    config.validate()
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Playwright is not installed. Install the project and run "
            "`python -m playwright install chromium`."
        ) from exc

    config.profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser_context = None
        try:
            browser_context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(config.profile_dir),
                headless=config.headless,
                viewport={
                    "width": config.browser_width,
                    "height": config.browser_height,
                },
            )
            page = (
                browser_context.pages[0]
                if browser_context.pages
                else browser_context.new_page()
            )
            page.goto(config.start_url, wait_until="domcontentloaded")

            if config.prompt_for_manual_navigation:
                LOGGER.info("Log in manually, then navigate to Likes, Saved, or a profile grid.")
                LOGGER.info("Come back here when the correct page is visible.")
                input("Press Enter to start scraping the active page...")

            return scan_page_for_instagram_urls(page, config)
        finally:
            if browser_context is not None:
                browser_context.close()
