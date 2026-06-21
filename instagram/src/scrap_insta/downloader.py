from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .models import DownloadConfig, DownloadItemResult, RunReport
from .urls import deduplicate_normalized_urls

LOGGER = logging.getLogger(__name__)


def _load_youtube_dl_class() -> type[Any]:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp is not installed. Install the project with `python -m pip install -e .`."
        ) from exc
    return YoutubeDL


def _archive_file_for(config: DownloadConfig) -> Path:
    return config.archive_file or config.output_dir / "downloaded_archive.txt"


def _build_ydl_options(config: DownloadConfig) -> dict[str, Any]:
    options: dict[str, Any] = {
        "outtmpl": str(config.output_dir / "%(uploader|unknown)s_%(id)s.%(ext)s"),
        "download_archive": str(_archive_file_for(config)),
        "ignoreerrors": False,
        "noplaylist": True,
        "retries": config.retries,
        "continuedl": True,
        "overwrites": not config.skip_existing,
    }

    if config.cookies_from_browser is not None:
        options["cookiesfrombrowser"] = (config.cookies_from_browser,)
    if config.cookies_file is not None:
        options["cookiefile"] = str(config.cookies_file)

    return options


def _output_path_for(downloader: Any, info: dict[str, Any] | None) -> str | None:
    if not info:
        return None
    try:
        return str(downloader.prepare_filename(info))
    except Exception:
        return None


def download_urls(
    config: DownloadConfig,
    youtube_dl_class: type[Any] | None = None,
) -> RunReport:
    config.validate()
    report = RunReport(
        command=config.command,
        metadata={
            "dry_run": config.dry_run,
            "output_dir": str(config.output_dir),
            "archive_file": str(_archive_file_for(config)),
        },
    )

    normalized_urls, invalid_urls = deduplicate_normalized_urls(config.urls)
    for invalid_url in invalid_urls:
        report.items.append(
            DownloadItemResult(
                url=invalid_url,
                source=config.source,
                status="failed",
                error="Invalid or unsupported Instagram URL.",
            )
        )

    if config.dry_run:
        for url in normalized_urls:
            report.items.append(
                DownloadItemResult(url=url, source=config.source, status="dry_run")
            )
        return report.finish()

    if not normalized_urls:
        LOGGER.warning("No URL to download.")
        return report.finish()

    config.output_dir.mkdir(parents=True, exist_ok=True)
    _archive_file_for(config).parent.mkdir(parents=True, exist_ok=True)
    downloader_type = youtube_dl_class or _load_youtube_dl_class()
    options = _build_ydl_options(config)

    with downloader_type(options) as downloader:
        for url in normalized_urls:
            try:
                info = downloader.extract_info(url, download=True)
            except Exception as exc:
                report.items.append(
                    DownloadItemResult(
                        url=url,
                        source=config.source,
                        status="failed",
                        error=str(exc),
                    )
                )
                continue

            if info is None:
                report.items.append(
                    DownloadItemResult(
                        url=url,
                        source=config.source,
                        status="failed",
                        error="yt-dlp returned no metadata.",
                    )
                )
                continue

            report.items.append(
                DownloadItemResult(
                    url=url,
                    source=config.source,
                    status="downloaded",
                    output_path=_output_path_for(downloader, info),
                )
            )

    return report.finish()


def download_instagram_urls(
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
