from __future__ import annotations

from dataclasses import replace

from .models import DownloadItemResult, RunReport


def annotate_duplicates(report: RunReport) -> RunReport:
    first_url_by_key: dict[str, str] = {}
    annotated_items: list[DownloadItemResult] = []

    for item in report.items:
        duplicate_key = item.media_id or item.output_path
        if not duplicate_key:
            annotated_items.append(item)
            continue

        original_url = first_url_by_key.get(duplicate_key)
        if original_url is None:
            first_url_by_key[duplicate_key] = item.url
            annotated_items.append(item)
            continue

        annotated_items.append(replace(item, duplicate_of=original_url))

    report.items = annotated_items
    duplicate_count = sum(1 for item in report.items if item.duplicate_of)
    report.metadata["duplicate_count"] = duplicate_count
    return report


def duplicate_groups(report: RunReport) -> list[list[DownloadItemResult]]:
    groups: dict[str, list[DownloadItemResult]] = {}
    for item in report.items:
        duplicate_key = item.media_id or item.output_path
        if duplicate_key:
            groups.setdefault(duplicate_key, []).append(item)
    return [items for items in groups.values() if len(items) > 1]
