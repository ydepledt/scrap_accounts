from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Protocol

from .models import DownloadItemResult, RunReport
from .url_rules import PlatformUrlRules

LOGGER = logging.getLogger(__name__)
HASHTAG_RE = re.compile(r"(?<!\w)#(\w+)", re.UNICODE)


class DownloadConfigProtocol(Protocol):
    urls: list[str]
    output_dir: Path
    cookies_from_browser: str | None
    cookies_file: Path | None
    archive_file: Path | None
    retries: int
    comments_limit: int
    format_selector: str | None
    audio_only: bool
    write_thumbnail: bool
    metadata_only: bool
    skip_existing: bool
    dry_run: bool
    command: str
    source: str

    def validate(self) -> None: ...


def load_youtube_dl_class() -> type[Any]:
    try:
        from yt_dlp import YoutubeDL
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "yt-dlp is not installed. Install the project with `python -m pip install -e .`."
        ) from exc
    return YoutubeDL


class YtDlpMediaDownloader:
    def __init__(
        self,
        url_rules: PlatformUrlRules,
        invalid_url_message: str,
    ) -> None:
        self.url_rules = url_rules
        self.invalid_url_message = invalid_url_message

    def archive_file_for(self, config: DownloadConfigProtocol) -> Path:
        return config.archive_file or config.output_dir / "downloaded_archive.txt"

    def build_options(self, config: DownloadConfigProtocol) -> dict[str, Any]:
        options: dict[str, Any] = {
            "outtmpl": str(config.output_dir / "%(uploader|channel|unknown)s_%(id)s.%(ext)s"),
            "download_archive": str(self.archive_file_for(config)),
            "ignoreerrors": False,
            "noplaylist": not bool(getattr(config, "include_playlists", False)),
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

    def download(
        self,
        config: DownloadConfigProtocol,
        youtube_dl_class: type[Any] | None = None,
    ) -> RunReport:
        config.validate()
        report = RunReport(
            command=config.command,
            metadata={
                "dry_run": config.dry_run,
                "output_dir": str(config.output_dir),
                "archive_file": str(self.archive_file_for(config)),
                "comments_limit": config.comments_limit,
                "include_playlists": bool(getattr(config, "include_playlists", False)),
                "platform": self.url_rules.name,
            },
        )

        normalized_urls, invalid_urls = self.url_rules.deduplicate_normalized_urls(config.urls)
        for invalid_url in invalid_urls:
            report.items.append(
                DownloadItemResult(
                    url=invalid_url,
                    source=config.source,
                    status="failed",
                    error_type="invalid_url",
                    error=self.invalid_url_message,
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
        self.archive_file_for(config).parent.mkdir(parents=True, exist_ok=True)
        downloader_type = youtube_dl_class or load_youtube_dl_class()
        options = self.build_options(config)

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

                main_info = _primary_media_info(info)
                media_files = [] if config.metadata_only else _media_file_paths(downloader, info)
                metadata = _metadata_for(main_info)
                if media_files:
                    metadata["media_files"] = media_files
                entries = _media_entries(info)
                if entries:
                    metadata["carousel_entries"] = [_metadata_for(entry) for entry in entries[:30]]
                report.items.append(
                    DownloadItemResult(
                        url=url,
                        source=config.source,
                        status="metadata" if config.metadata_only else "downloaded",
                        output_path=media_files[0] if media_files else None,
                        media_id=_media_id_for(main_info),
                        description=(description := _description_for(main_info)),
                        tags=_tags_for(main_info, description),
                        comments=_comments_for(main_info, config.comments_limit),
                        stats=_stats_for(main_info),
                        metadata=metadata,
                    )
                )

        return report.finish()


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


def _stats_for(info: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "view_count",
        "like_count",
        "comment_count",
        "repost_count",
        "retweet_count",
        "reply_count",
        "favorite_count",
        "duration",
        "upload_date",
        "channel",
        "channel_id",
        "uploader",
        "uploader_id",
        "playlist",
        "playlist_id",
    )
    return {
        field_name: info[field_name]
        for field_name in fields
        if info.get(field_name) is not None
    }


def _media_id_for(info: dict[str, Any]) -> str | None:
    extractor_key = info.get("extractor_key") or info.get("extractor")
    raw_id = info.get("id")
    if not raw_id:
        return None
    if extractor_key:
        return f"{extractor_key}:{raw_id}"
    return str(raw_id)


# Explicit allowlist: do not export extractor headers, cookies or signed media URLs.
_METADATA_FIELDS = (
    "title", "fulltitle", "alt_title", "display_id", "webpage_url",
    "uploader", "uploader_id", "uploader_url", "channel", "channel_id",
    "channel_url", "creator", "timestamp", "release_timestamp",
    "upload_date", "release_date", "duration", "thumbnail", "width",
    "height", "fps", "resolution", "ext", "language", "categories",
    "availability", "age_limit", "license", "location", "artist",
    "track", "album", "extractor", "extractor_key",
)


def _metadata_for(info: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for field in _METADATA_FIELDS:
        value = info.get(field)
        if isinstance(value, (str, int, float, bool)):
            metadata[field] = value
        elif isinstance(value, (list, tuple)):
            # Categories and other user-visible labels, not arbitrary extractor objects.
            labels = [label for label in value if isinstance(label, str)]
            if labels:
                metadata[field] = labels[:100]
    return metadata


def _media_entries(info: dict[str, Any]) -> list[dict[str, Any]]:
    entries = info.get("entries")
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _primary_media_info(info: dict[str, Any]) -> dict[str, Any]:
    """Keep post-level metadata, filling absent fields from a carousel's first item."""
    entries = _media_entries(info)
    if not entries:
        return info
    merged = dict(entries[0])
    merged.update({key: value for key, value in info.items() if key != "entries" and value is not None})
    return merged


def _media_file_paths(downloader: Any, info: dict[str, Any]) -> list[str]:
    """Include every locally downloaded carousel item, not only a synthetic post path."""
    paths: list[str] = []
    for entry in _media_entries(info) or [info]:
        requested = entry.get("requested_downloads")
        if isinstance(requested, list):
            for item in requested:
                if isinstance(item, dict) and isinstance(item.get("filepath"), str):
                    paths.append(item["filepath"])
        if not requested:
            path = _output_path_for(downloader, entry)
            if path:
                paths.append(path)
    return list(dict.fromkeys(paths))
