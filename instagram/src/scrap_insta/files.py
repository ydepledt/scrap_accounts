from __future__ import annotations

from pathlib import Path

from .urls import deduplicate_normalized_urls, extract_urls_from_text


def load_urls_from_file(urls_file: Path) -> list[str]:
    if not urls_file.exists():
        raise FileNotFoundError(f"URL file not found: {urls_file}")
    return extract_urls_from_text(urls_file.read_text(encoding="utf-8"))


def write_urls_to_file(urls: list[str], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(urls)
    if content:
        content += "\n"
    output_file.write_text(content, encoding="utf-8")


def merge_url_lists(*url_lists: list[str]) -> list[str]:
    merged: list[str] = []
    for urls in url_lists:
        merged.extend(urls)
    normalized_urls, _invalid_urls = deduplicate_normalized_urls(merged)
    return normalized_urls


def diff_url_files(old_file: Path, new_file: Path) -> dict[str, list[str]]:
    old_urls = set(load_urls_from_file(old_file))
    new_urls = set(load_urls_from_file(new_file))
    return {
        "added": sorted(new_urls - old_urls),
        "removed": sorted(old_urls - new_urls),
        "shared": sorted(old_urls & new_urls),
    }
