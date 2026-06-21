from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

SUPPORTED_CONTENT_PATH = re.compile(r"^/(reel|p|tv)/[A-Za-z0-9_-]+/?$", re.IGNORECASE)
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.|m\.)?instagram\.com/(?:reel|p|tv)/[A-Za-z0-9_-]+/?(?:[?#][^\s<>'\"]*)?",
    re.IGNORECASE,
)
SUPPORTED_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}


def normalize_instagram_url(raw_url: str) -> str | None:
    cleaned_url = raw_url.strip().strip("<>()[]{}.,;\"'")
    parsed_url = urlparse(cleaned_url)

    if parsed_url.scheme.lower() not in {"http", "https"}:
        return None

    host = (parsed_url.hostname or "").lower()
    if host not in SUPPORTED_HOSTS:
        return None

    if not SUPPORTED_CONTENT_PATH.fullmatch(parsed_url.path):
        return None

    normalized_path = parsed_url.path.rstrip("/") + "/"
    return urlunparse(("https", "www.instagram.com", normalized_path, "", "", ""))


def extract_urls_from_text(raw_text: str) -> list[str]:
    normalized_urls = {
        normalized_url
        for raw_url in INSTAGRAM_URL_PATTERN.findall(raw_text)
        if (normalized_url := normalize_instagram_url(raw_url)) is not None
    }
    return sorted(normalized_urls)


def deduplicate_normalized_urls(raw_urls: list[str]) -> tuple[list[str], list[str]]:
    normalized_urls: list[str] = []
    invalid_urls: list[str] = []
    seen: set[str] = set()

    for raw_url in raw_urls:
        normalized_url = normalize_instagram_url(raw_url)
        if normalized_url is None:
            invalid_urls.append(raw_url)
            continue
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        normalized_urls.append(normalized_url)

    return normalized_urls, invalid_urls
