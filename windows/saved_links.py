from __future__ import annotations

"""Read and filter URL lists already collected by the desktop app."""

from pathlib import Path
from urllib.parse import urlsplit

_ALLOWED_HOSTS = {
    "Instagram": frozenset({"instagram.com", "www.instagram.com", "m.instagram.com"}),
    "X": frozenset({"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}),
    "YouTube": frozenset({"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "music.youtube.com"}),
}


def saved_url_file(root: Path, platform: str) -> Path:
    if platform not in _ALLOWED_HOSTS:
        raise ValueError(f"Unsupported platform: {platform}")
    return root / platform / "urls.txt"


def load_saved_urls(path: Path, platform: str) -> list[str]:
    """Keep first occurrence of each valid platform URL without changing the file."""
    hosts = _ALLOWED_HOSTS[platform]
    if not path.is_file():
        return []
    urls: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        url = line.strip()
        if not url or url in seen:
            continue
        try:
            parsed = urlsplit(url)
            valid = parsed.scheme == "https" and parsed.hostname in hosts and not parsed.username
        except ValueError:
            valid = False
        if valid:
            urls.append(url)
            seen.add(url)
    return urls


def filter_saved_urls(urls: list[str], query: str) -> list[str]:
    needle = query.strip().casefold()
    return [url for url in urls if needle in url.casefold()] if needle else list(urls)


def pick_saved_urls(visible_urls: list[str], positions: tuple[int, ...]) -> list[str]:
    """Translate the listbox's filtered indexes back into concrete URLs."""
    return [visible_urls[index] for index in sorted(set(positions)) if 0 <= index < len(visible_urls)]
