from __future__ import annotations

from pathlib import Path

from .urls import extract_urls_from_text


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
