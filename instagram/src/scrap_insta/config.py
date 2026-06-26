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
    instagram_login_url: str
    cookie_browser_choices: tuple[str, ...]


def load_config() -> AppConfig:
    config_file = files(__package__).joinpath("config.toml")
    with config_file.open("rb") as stream:
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
        instagram_login_url=scrape["start_url"],
        cookie_browser_choices=tuple(download["cookie_browser_choices"]),
    )


CONFIG = load_config()
