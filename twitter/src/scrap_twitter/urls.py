from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from scrap_common.url_rules import PlatformUrlRules

TWITTER_PATH_PATTERN = re.compile(
    r"^/(?:[A-Za-z0-9_]{1,15}|i)/(?:status|statuses)/\d+"
    r"(?:/(?:photo|video)/\d+)?/?$",
    re.IGNORECASE,
)
TWITTER_URL_PATTERN = re.compile(
    r"https?://(?:www\.|mobile\.|m\.)?(?:x|twitter)\.com/"
    r"(?:[A-Za-z0-9_]{1,15}|i)/(?:status|statuses)/\d+"
    r"(?:/(?:photo|video)/\d+)?/?(?:[?#][^\s<>'\"]*)?",
    re.IGNORECASE,
)
SUPPORTED_HOSTS = {
    "x.com",
    "www.x.com",
    "mobile.x.com",
    "m.x.com",
    "twitter.com",
    "www.twitter.com",
    "mobile.twitter.com",
    "m.twitter.com",
}


class TwitterUrlRules(PlatformUrlRules):
    def normalize_url(self, raw_url: str) -> str | None:
        parsed_url = urlparse(raw_url.strip().strip("<>()[]{}.,;\"'"))
        host = (parsed_url.hostname or "").lower()
        if parsed_url.scheme.lower() not in {"http", "https"} or host not in self.supported_hosts:
            return None

        if not self.content_path_pattern or not self.content_path_pattern.fullmatch(parsed_url.path):
            return None

        parts = [part for part in parsed_url.path.strip("/").split("/") if part]
        if len(parts) < 3:
            return None

        account = parts[0].lower()
        status_id = parts[2]
        normalized_path = f"/{account}/status/{status_id}/"
        return urlunparse(("https", self.canonical_host, normalized_path, "", "", ""))


TWITTER_URL_RULES = TwitterUrlRules(
    name="twitter",
    supported_hosts=frozenset(SUPPORTED_HOSTS),
    canonical_host="x.com",
    content_path_pattern=TWITTER_PATH_PATTERN,
    text_url_pattern=TWITTER_URL_PATTERN,
    visible_href_fragments=("/status/", "/statuses/"),
)


def normalize_twitter_url(raw_url: str) -> str | None:
    return TWITTER_URL_RULES.normalize_url(raw_url)


def extract_urls_from_text(raw_text: str) -> list[str]:
    return TWITTER_URL_RULES.extract_urls_from_text(raw_text)


def deduplicate_normalized_urls(raw_urls: list[str]) -> tuple[list[str], list[str]]:
    return TWITTER_URL_RULES.deduplicate_normalized_urls(raw_urls)
