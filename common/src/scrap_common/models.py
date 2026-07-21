from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class DownloadItemResult:
    url: str
    source: str
    status: str
    output_path: str | None = None
    media_id: str | None = None
    duplicate_of: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    comments: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source": self.source,
            "status": self.status,
            "output_path": self.output_path,
            "media_id": self.media_id,
            "duplicate_of": self.duplicate_of,
            "description": self.description,
            "tags": self.tags,
            "comments": self.comments,
            "stats": self.stats,
            "error_type": self.error_type,
            "error": self.error,
        }


@dataclass
class RunReport:
    command: str
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str | None = None
    items: list[DownloadItemResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self) -> "RunReport":
        self.finished_at = utc_now_iso()
        return self

    @property
    def total_urls(self) -> int:
        return len(self.items)

    @property
    def failed_count(self) -> int:
        return self.status_counts().get("failed", 0)

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item.status] = counts.get(item.status, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_urls": self.total_urls,
            "status_counts": self.status_counts(),
            "metadata": self.metadata,
            "items": [item.to_dict() for item in self.items],
        }
