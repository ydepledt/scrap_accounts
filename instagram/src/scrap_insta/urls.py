from __future__ import annotations

import re

from scrap_common.url_rules import PlatformUrlRules

SUPPORTED_CONTENT_PATH = re.compile(r"^/(reel|p|tv)/[A-Za-z0-9_-]+/?$", re.IGNORECASE)
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.|m\.)?instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+/?(?:[?#][^\s<>'\"]*)?",
    re.IGNORECASE,
)
SUPPORTED_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
INSTAGRAM_URL_RULES = PlatformUrlRules(
    name="instagram",
    supported_hosts=frozenset(SUPPORTED_HOSTS),
    canonical_host="www.instagram.com",
    content_path_pattern=SUPPORTED_CONTENT_PATH,
    text_url_pattern=INSTAGRAM_URL_PATTERN,
    visible_href_fragments=("/reel/", "/p/", "/tv/"),
)


def normalize_instagram_url(raw_url: str) -> str | None:
    return INSTAGRAM_URL_RULES.normalize_url(raw_url)


def extract_urls_from_text(raw_text: str) -> list[str]:
    return INSTAGRAM_URL_RULES.extract_urls_from_text(raw_text)


def deduplicate_normalized_urls(raw_urls: list[str]) -> tuple[list[str], list[str]]:
    return INSTAGRAM_URL_RULES.deduplicate_normalized_urls(raw_urls)
