from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import DownloadItemResult, RunReport

REPORT_FIELDS = (
    "url",
    "source",
    "status",
    "output_path",
    "media_id",
    "duplicate_of",
    "description",
    "tags",
    "comments",
    "stats",
    "metadata",
    "error_type",
    "error",
)


def write_json_report(report: RunReport, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_csv_report(report: RunReport, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for item in report.items:
            row = item.to_dict()
            row["tags"] = json.dumps(row["tags"], ensure_ascii=False)
            row["comments"] = json.dumps(row["comments"], ensure_ascii=False)
            row["stats"] = json.dumps(row["stats"], ensure_ascii=False)
            row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False)
            writer.writerow(row)


def write_report_files(
    report: RunReport,
    output_dir: Path,
    stem: str | None = None,
) -> tuple[Path, Path]:
    report_stem = stem or f"{report.command}_report"
    json_path = output_dir / f"{report_stem}.json"
    csv_path = output_dir / f"{report_stem}.csv"
    write_json_report(report, json_path)
    write_csv_report(report, csv_path)
    return json_path, csv_path


def summarize_report(report: RunReport, top: int = 10) -> dict[str, Any]:
    tag_counts: dict[str, int] = {}
    comment_count = 0
    failed_urls: list[str] = []
    view_count = 0
    like_count = 0

    for item in report.items:
        for tag in item.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        if item.status == "failed":
            failed_urls.append(item.url)
        comment_count += len(item.comments)
        view_count += int(item.stats.get("view_count") or 0)
        like_count += int(item.stats.get("like_count") or 0)

    return {
        "command": report.command,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "total_urls": report.total_urls,
        "status_counts": report.status_counts(),
        "top_tags": sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:top],
        "comment_count": comment_count,
        "view_count": view_count,
        "like_count": like_count,
        "failed_urls": failed_urls,
    }
