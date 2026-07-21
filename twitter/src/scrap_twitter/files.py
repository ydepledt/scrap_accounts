from __future__ import annotations

from pathlib import Path

from .urls import extract_urls_from_text


def load_urls_from_file(input_file: Path) -> list[str]:
    if not input_file.exists():
        raise FileNotFoundError(f"URL file not found: {input_file}")
    return extract_urls_from_text(input_file.read_text(encoding="utf-8"))


def write_urls_to_file(urls: list[str], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{url}\n" for url in sorted(dict.fromkeys(urls)))
    output_file.write_text(content, encoding="utf-8")


def merge_url_lists(*url_lists: list[str]) -> list[str]:
    merged: list[str] = []
    for url_list in url_lists:
        merged.extend(url_list)
    return sorted(dict.fromkeys(merged))
