from __future__ import annotations

from dataclasses import dataclass
from re import Pattern
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


@dataclass(frozen=True)
class PlatformUrlRules:
    name: str
    supported_hosts: frozenset[str]
    canonical_host: str
    content_path_pattern: Pattern[str] | None
    text_url_pattern: Pattern[str]
    visible_href_fragments: tuple[str, ...]
    query_keys: tuple[str, ...] = ()
    short_host: str | None = None

    def normalize_url(self, raw_url: str) -> str | None:
        cleaned_url = raw_url.strip().strip("<>()[]{}.,;\"'")
        parsed_url = urlparse(cleaned_url)

        if parsed_url.scheme.lower() not in {"http", "https"}:
            return None

        host = (parsed_url.hostname or "").lower()
        if host not in self.supported_hosts:
            return None

        if self.short_host and host == self.short_host:
            code = parsed_url.path.strip("/").split("/", 1)[0]
            return self._canonical_path_url(f"/watch", {"v": code}) if code else None

        query = parse_qs(parsed_url.query)
        if "v" in self.query_keys and query.get("v"):
            return self._canonical_path_url("/watch", {"v": query["v"][0]})
        if "list" in self.query_keys and query.get("list"):
            return self._canonical_path_url("/playlist", {"list": query["list"][0]})

        if self.content_path_pattern is None:
            return None
        if not self.content_path_pattern.fullmatch(parsed_url.path):
            return None

        normalized_path = parsed_url.path.rstrip("/") + "/"
        return urlunparse(("https", self.canonical_host, normalized_path, "", "", ""))

    def extract_urls_from_text(self, raw_text: str) -> list[str]:
        normalized_urls = {
            normalized_url
            for raw_url in self.text_url_pattern.findall(raw_text)
            if (normalized_url := self.normalize_url(raw_url)) is not None
        }
        return sorted(normalized_urls)

    def deduplicate_normalized_urls(self, raw_urls: list[str]) -> tuple[list[str], list[str]]:
        normalized_urls: list[str] = []
        invalid_urls: list[str] = []
        seen: set[str] = set()

        for raw_url in raw_urls:
            normalized_url = self.normalize_url(raw_url)
            if normalized_url is None:
                invalid_urls.append(raw_url)
                continue
            if normalized_url in seen:
                continue
            seen.add(normalized_url)
            normalized_urls.append(normalized_url)

        return normalized_urls, invalid_urls

    def visible_link_script(self) -> str:
        checks = " || ".join(
            f"href.includes({fragment!r})" for fragment in self.visible_href_fragments
        )
        return f"""
        () => Array.from(document.querySelectorAll('a[href]'))
            .map((anchor) => anchor.href)
            .filter((href) => ({checks}))
        """

    def _canonical_path_url(self, path: str, query: dict[str, str]) -> str:
        return urlunparse(
            (
                "https",
                self.canonical_host,
                path,
                "",
                urlencode(query),
                "",
            )
        )
