from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from tomllib import load


@dataclass(frozen=True)
class AppConfig:
    output_dir: Path
    profile_dir: Path
    urls_output: Path
    resolved_urls_output: Path
    scrolls: int
    scroll_delay_ms: int
    scroll_pixels: int
    browser_width: int
    browser_height: int
    max_idle_scrolls: int
    retries: int
    comments_limit: int
    format_selector: str | None
    audio_only: bool
    write_thumbnail: bool
    metadata_only: bool
    instagram_login_url: str
    cookie_browser_choices: tuple[str, ...]


def load_config(config_file: Path | None = None) -> AppConfig:
    config_source = (
        config_file
        if config_file is not None
        else files(__package__).joinpath("config.toml")
    )
    with config_source.open("rb") as stream:
        values = load(stream)

    paths = values["paths"]
    scrape = values["scrape"]
    download = values["download"]
    return AppConfig(
        output_dir=Path(paths["output_dir"]),
        profile_dir=Path(paths["profile_dir"]),
        urls_output=Path(paths["urls_output"]),
        resolved_urls_output=Path(paths["resolved_urls_output"]),
        scrolls=scrape["scrolls"],
        scroll_delay_ms=scrape["scroll_delay_ms"],
        scroll_pixels=scrape["scroll_pixels"],
        browser_width=scrape["browser_width"],
        browser_height=scrape["browser_height"],
        max_idle_scrolls=scrape["max_idle_scrolls"],
        retries=download["retries"],
        comments_limit=download["comments_limit"],
        format_selector=download.get("format_selector") or None,
        audio_only=download.get("audio_only", False),
        write_thumbnail=download.get("write_thumbnail", False),
        metadata_only=download.get("metadata_only", False),
        instagram_login_url=scrape["start_url"],
        cookie_browser_choices=tuple(download["cookie_browser_choices"]),
    )


CONFIG = load_config()
