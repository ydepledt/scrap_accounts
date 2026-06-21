from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .models import DownloadConfig, DownloadItemResult, DownloadReport, RunReport, ScrapeConfig
from .urls import extract_urls_from_text, normalize_instagram_url

try:
    __version__ = version("scrap-insta")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "DownloadConfig",
    "DownloadItemResult",
    "DownloadReport",
    "RunReport",
    "ScrapeConfig",
    "extract_urls_from_text",
    "normalize_instagram_url",
]
