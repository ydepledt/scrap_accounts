from __future__ import annotations

from pathlib import Path

from .models import RunReport
from .reports import write_report_files


def resolve_history_dir(output_dir: Path, history_dir: Path) -> Path:
    return history_dir if history_dir.is_absolute() else output_dir / history_dir


def run_id_for(report: RunReport) -> str:
    started_at = report.started_at.replace(":", "").replace("+", "Z")
    return f"{started_at}_{report.command}"


def write_history_report(
    report: RunReport,
    output_dir: Path,
    history_dir: Path,
) -> tuple[Path, Path]:
    run_id = run_id_for(report)
    report.metadata["run_id"] = run_id
    report.metadata["stable_report_dir"] = str(output_dir)

    run_dir = resolve_history_dir(output_dir, history_dir) / run_id
    report.metadata["run_dir"] = str(run_dir)
    return write_report_files(report, run_dir)
