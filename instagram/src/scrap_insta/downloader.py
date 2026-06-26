from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from .models import DownloadConfig, DownloadItemResult, RunReport
from .urls import deduplicate_normalized_urls

LOGGER = logging.getLogger(__name__)
HASHTAG_RE = re.compile(r"(?<!\w)#(\w+)", re.UNICODE)


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
        "getcomments": config.comments_limit > 0,
    }

    if config.format_selector is not None:
        options["format"] = config.format_selector
    if config.audio_only:
        options["format"] = config.format_selector or "bestaudio/best"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }
        ]
    if config.write_thumbnail:
        options["writethumbnail"] = True
    if config.metadata_only:
        options["skip_download"] = True

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


def _description_for(info: dict[str, Any]) -> str | None:
    for field_name in ("description", "title"):
        value = info.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _tags_for(info: dict[str, Any], description: str | None) -> list[str]:
    tags: list[str] = []
    raw_tags = info.get("tags")
    if isinstance(raw_tags, (list, tuple)):
        tags.extend(tag.strip().lstrip("#") for tag in raw_tags if isinstance(tag, str))
    if description:
        tags.extend(HASHTAG_RE.findall(description))

    return list(dict.fromkeys(tag for tag in tags if tag))


def _comments_for(info: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    if limit == 0:
        return []
    raw_comments = info.get("comments")
    if not isinstance(raw_comments, list):
        return []

    comments: list[dict[str, Any]] = []
    fields = ("id", "author", "author_id", "text", "timestamp", "like_count", "parent")
    for raw_comment in raw_comments:
        if not isinstance(raw_comment, dict):
            continue
        comment = {
            field_name: raw_comment[field_name]
            for field_name in fields
            if raw_comment.get(field_name) is not None
        }
        if comment:
            comments.append(comment)
        if len(comments) >= limit:
            break
    return comments


def classify_download_error(error: str) -> str:
    lowered = error.lower()
    if "invalid" in lowered or "unsupported" in lowered:
        return "invalid_url"
    if "login" in lowered or "cookie" in lowered or "sign in" in lowered:
        return "login_required"
    if "private" in lowered:
        return "private"
    if "not found" in lowered or "404" in lowered or "unavailable" in lowered:
        return "not_found"
    if "rate" in lowered or "too many requests" in lowered or "429" in lowered:
        return "rate_limited"
    return "yt_dlp_error"


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
            "comments_limit": config.comments_limit,
        },
    )

    normalized_urls, invalid_urls = deduplicate_normalized_urls(config.urls)
    for invalid_url in invalid_urls:
        report.items.append(
            DownloadItemResult(
                url=invalid_url,
                source=config.source,
                status="failed",
                error_type="invalid_url",
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
                info = downloader.extract_info(url, download=not config.metadata_only)
            except Exception as exc:
                error = str(exc)
                report.items.append(
                    DownloadItemResult(
                        url=url,
                        source=config.source,
                        status="failed",
                        error_type=classify_download_error(error),
                        error=error,
                    )
                )
                continue

            if info is None:
                report.items.append(
                    DownloadItemResult(
                        url=url,
                        source=config.source,
                        status="failed",
                        error_type="yt_dlp_error",
                        error="yt-dlp returned no metadata.",
                    )
                )
                continue

            report.items.append(
                # yt-dlp exposes captions as `description`, post hashtags as
                # `tags`, and extractor-supported comments as `comments`.
                DownloadItemResult(
                    url=url,
                    source=config.source,
                    status="metadata" if config.metadata_only else "downloaded",
                    output_path=(
                        None
                        if config.metadata_only
                        else _output_path_for(downloader, info)
                    ),
                    description=(description := _description_for(info)),
                    tags=_tags_for(info, description),
                    comments=_comments_for(info, config.comments_limit),
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
