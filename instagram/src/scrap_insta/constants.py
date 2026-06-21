from __future__ import annotations

from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("instagram_downloads")
DEFAULT_PROFILE_DIR = Path(".instagram_playwright_profile")
DEFAULT_URLS_OUTPUT = Path("scraped_instagram_urls.txt")
DEFAULT_RESOLVED_URLS_OUTPUT = Path("resolved_instagram_urls.txt")
DEFAULT_SCROLLS = 60
DEFAULT_SCROLL_DELAY_MS = 1200
DEFAULT_SCROLL_PIXELS = 1800
DEFAULT_BROWSER_WIDTH = 1280
DEFAULT_BROWSER_HEIGHT = 900
DEFAULT_MAX_IDLE_SCROLLS = 5
DEFAULT_RETRIES = 3
INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"

COOKIE_BROWSER_CHOICES = (
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
)
