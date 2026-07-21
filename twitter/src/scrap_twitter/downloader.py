from __future__ import annotations

from pathlib import Path
from typing import Any

from scrap_common.downloader import YtDlpMediaDownloader, classify_download_error

from .models import DownloadConfig, RunReport
from .urls import TWITTER_URL_RULES

TWITTER_DOWNLOADER = YtDlpMediaDownloader(
    TWITTER_URL_RULES,
    "Invalid or unsupported Twitter/X URL.",
)


def download_urls(
    config: DownloadConfig,
    twitter_dl_class: type[Any] | None = None,
) -> RunReport:
    return TWITTER_DOWNLOADER.download(config, twitter_dl_class)


def download_twitter_urls(
    urls: list[str],
    output_dir: Path,
    cookies_from_browser: str | None = None,
) -> None:
    report = download_urls(
        DownloadConfig(
            urls=urls,
            output_dir=output_dir,
            cookies_from_browser=cookies_from_browser,
        )
    )
    if report.failed_count:
        raise RuntimeError(f"Download failed for {report.failed_count} URL(s).")


__all__ = ["classify_download_error", "download_urls", "download_twitter_urls"]
