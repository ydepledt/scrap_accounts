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
    "description",
    "tags",
    "comments",
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


def read_report_file(report_file: Path) -> RunReport:
    if not report_file.exists():
        raise FileNotFoundError(f"Report file not found: {report_file}")

    payload = json.loads(report_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Report file must contain a JSON object: {report_file}")

    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Report field `items` must be a list.")

    items: list[DownloadItemResult] = []
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        items.append(
            DownloadItemResult(
                url=str(raw_item.get("url", "")),
                source=str(raw_item.get("source", "")),
                status=str(raw_item.get("status", "")),
                output_path=_optional_str(raw_item.get("output_path")),
                description=_optional_str(raw_item.get("description")),
                tags=_string_list(raw_item.get("tags")),
                comments=_dict_list(raw_item.get("comments")),
                error_type=_optional_str(raw_item.get("error_type")),
                error=_optional_str(raw_item.get("error")),
            )
        )

    report = RunReport(
        command=str(payload.get("command", "unknown")),
        started_at=str(payload.get("started_at", "")),
        finished_at=_optional_str(payload.get("finished_at")),
        items=items,
        metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
    )
    return report


def summarize_report(report: RunReport, top: int = 10) -> dict[str, Any]:
    tag_counts: dict[str, int] = {}
    error_type_counts: dict[str, int] = {}
    comment_count = 0
    failed_urls: list[str] = []
    output_paths: list[str] = []

    for item in report.items:
        for tag in item.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        if item.error_type:
            error_type_counts[item.error_type] = error_type_counts.get(item.error_type, 0) + 1
        if item.status == "failed":
            failed_urls.append(item.url)
        if item.output_path:
            output_paths.append(item.output_path)
        comment_count += len(item.comments)

    return {
        "command": report.command,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "total_urls": report.total_urls,
        "status_counts": report.status_counts(),
        "error_type_counts": dict(sorted(error_type_counts.items())),
        "top_tags": sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:top],
        "comment_count": comment_count,
        "failed_urls": failed_urls,
        "output_paths": output_paths,
    }


def failed_urls_from_report(report: RunReport) -> list[str]:
    return [item.url for item in report.items if item.status == "failed" and item.url]


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
