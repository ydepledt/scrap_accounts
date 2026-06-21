from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import RunReport

REPORT_FIELDS = ("url", "source", "status", "output_path", "error")


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
            writer.writerow(item.to_dict())


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
