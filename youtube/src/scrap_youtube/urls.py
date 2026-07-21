from __future__ import annotations

import re

from scrap_common.url_rules import PlatformUrlRules

YOUTUBE_PATH_PATTERN = re.compile(r"^/(shorts|live)/[A-Za-z0-9_-]{6,}/?$", re.IGNORECASE)
YOUTUBE_URL_PATTERN = re.compile(
    r"https?://(?:(?:www\.|m\.|music\.)?youtube\.com/"
    r"(?:watch\?[^\s<>'\"]*v=[A-Za-z0-9_-]{6,}[^\s<>'\"]*"
    r"|shorts/[A-Za-z0-9_-]{6,}/?(?:[?#][^\s<>'\"]*)?"
    r"|live/[A-Za-z0-9_-]{6,}/?(?:[?#][^\s<>'\"]*)?"
    r"|playlist\?[^\s<>'\"]*list=[A-Za-z0-9_-]+[^\s<>'\"]*)"
    r"|youtu\.be/[A-Za-z0-9_-]{6,}/?(?:[?#][^\s<>'\"]*)?)",
    re.IGNORECASE,
)
SUPPORTED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}
YOUTUBE_URL_RULES = PlatformUrlRules(
    name="youtube",
    supported_hosts=frozenset(SUPPORTED_HOSTS),
    canonical_host="www.youtube.com",
    content_path_pattern=YOUTUBE_PATH_PATTERN,
    text_url_pattern=YOUTUBE_URL_PATTERN,
    visible_href_fragments=("/watch?", "/shorts/", "/live/", "/playlist?"),
    query_keys=("v", "list"),
    short_host="youtu.be",
)


def normalize_youtube_url(raw_url: str) -> str | None:
    return YOUTUBE_URL_RULES.normalize_url(raw_url)


def extract_urls_from_text(raw_text: str) -> list[str]:
    return YOUTUBE_URL_RULES.extract_urls_from_text(raw_text)


def deduplicate_normalized_urls(raw_urls: list[str]) -> tuple[list[str], list[str]]:
    return YOUTUBE_URL_RULES.deduplicate_normalized_urls(raw_urls)
