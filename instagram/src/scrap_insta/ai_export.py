from __future__ import annotations

"""Local, API-ready Instagram export. No network or AI call is made here."""

import csv
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import DownloadItemResult, RunReport

_HASHTAG = re.compile(r"(?<!\\w)#(\\w+)", re.UNICODE)
_CSV_COLUMNS = (
    "url", "status", "title", "caption", "hashtags", "username",
    "published_at", "media_type", "media_path", "thumbnail_url",
    "duration_seconds", "views", "likes", "comments_reported",
    "comments_collected", "comments_status", "error",
)


def _iso_date(meta: dict[str, Any]) -> str | None:
    timestamp = meta.get("timestamp") or meta.get("release_timestamp")
    if isinstance(timestamp, (float, int)):
        try:
            return datetime.fromtimestamp(timestamp, UTC).isoformat(timespec="seconds")
        except (OverflowError, OSError, ValueError):
            pass
    date = meta.get("upload_date") or meta.get("release_date")
    if isinstance(date, str) and re.fullmatch(r"\\d{8}", date):
        try:
            return datetime.strptime(date, "%Y%m%d").date().isoformat()
        except ValueError:
            pass
    return None


def _hashtags(caption: str | None) -> list[str]:
    return list(dict.fromkeys(match.lower() for match in _HASHTAG.findall(caption or "")))


def _comments_state(item: DownloadItemResult, limit: int) -> str:
    if limit <= 0:
        return "disabled"
    if item.status in {"failed", "dry_run"}:
        return "unavailable"
    if len(item.comments) >= limit:
        return "limit_reached"
    if item.comments:
        return "partial_or_unverified"
    if item.stats.get("comment_count") == 0:
        return "zero_reported"
    return "not_returned_by_extractor"


def record_for_item(item: DownloadItemResult, comments_limit: int = 0) -> dict[str, Any]:
    """One JSON-safe record per input URL, including failures and missing-data markers."""
    meta = item.metadata
    username = meta.get("uploader_id") or meta.get("uploader")
    title = meta.get("title") or meta.get("fulltitle") or meta.get("alt_title")
    caption = item.description
    hashtags = _hashtags(caption)
    comments = item.comments
    # Representative texts only, without comment authors, for a cheaper future API call.
    useful = [comment for comment in comments if str(comment.get("text") or "").strip()]
    useful.sort(key=lambda comment: _int_or_zero(comment.get("like_count")), reverse=True)
    representative = [
        str(comment["text"]).strip()[:500]
        for comment in useful[:30]
    ]
    path = item.url.split("?")[0]
    media_type = (
        "video" if "/reel/" in path or "/tv/" in path
        else "image" if meta.get("ext") in {"jpg", "jpeg", "png", "webp"}
        else "post_or_carousel"
    )
    return {
        "schema_version": "instagram.ai.v1",
        "platform": "instagram",
        "url": item.url,
        "media_id": item.media_id,
        "status": item.status,
        "duplicate_of": item.duplicate_of,
        "title": title,
        "caption": caption,
        "hashtags": hashtags,
        "tags": item.tags,
        "author": {
            "username": username,
            "display_name": meta.get("uploader") or meta.get("channel"),
            "id": meta.get("uploader_id") or meta.get("channel_id"),
            "profile_url": meta.get("uploader_url") or meta.get("channel_url"),
        },
        "published_at": _iso_date(meta),
        "language": meta.get("language"),
        "media": {
            "type": media_type,
            "local_path": item.output_path,
            "thumbnail_url": meta.get("thumbnail"),
            "duration_seconds": meta.get("duration") or item.stats.get("duration"),
            "width": meta.get("width"),
            "height": meta.get("height"),
            "fps": meta.get("fps"),
            "file_extension": meta.get("ext"),
        },
        "engagement": {
            "views": item.stats.get("view_count"),
            "likes": item.stats.get("like_count"),
            "comments_reported": item.stats.get("comment_count"),
            "reposts": item.stats.get("repost_count"),
        },
        "comments": comments,
        "comments_retrieval": {
            "requested_limit": comments_limit,
            "collected_count": len(comments),
            "status": _comments_state(item, comments_limit),
            "source": "yt_dlp" if comments else None,
            "exhaustive": False,
        },
        "source_metadata": meta,
        "ai_input": {
            "title": title,
            "caption": caption,
            "hashtags": hashtags,
            "representative_comments": representative,
            "local_media_path": item.output_path,
            "instruction_hint": (
                "Analyse aussi les images et l'audio du média, si accessibles. "
                "Le texte seul ne suffit pas toujours à distinguer humour, conseils, jeux ou autres."
            ),
        },
        "error": item.error,
        "error_type": item.error_type,
    }


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def write_ai_export(report: RunReport, output_dir: Path) -> tuple[Path, Path]:
    """Write full JSONL records and an easy-to-browse CSV summary."""
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "analysis_ready.jsonl"
    csv_path = output_dir / "analysis_ready.csv"
    comment_limit = _int_or_zero(report.metadata.get("comments_limit"))
    records = [record_for_item(item, comment_limit) for item in report.items]

    with jsonl_path.open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\\n")

    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for record in records:
            engagement = record["engagement"]
            media = record["media"]
            writer.writerow({
                "url": record["url"],
                "status": record["status"],
                "title": record["title"],
                "caption": record["caption"],
                "hashtags": " ".join("#" + tag for tag in record["hashtags"]),
                "username": record["author"]["username"],
                "published_at": record["published_at"],
                "media_type": media["type"],
                "media_path": media["local_path"],
                "thumbnail_url": media["thumbnail_url"],
                "duration_seconds": media["duration_seconds"],
                "views": engagement["views"],
                "likes": engagement["likes"],
                "comments_reported": engagement["comments_reported"],
                "comments_collected": record["comments_retrieval"]["collected_count"],
                "comments_status": record["comments_retrieval"]["status"],
                "error": record["error"],
            })
    return jsonl_path, csv_path
