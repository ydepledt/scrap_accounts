from __future__ import annotations

import csv
import json

import pytest

from scrap_insta.files import load_urls_from_file, write_urls_to_file
from scrap_insta.models import DownloadItemResult, RunReport
from scrap_insta.reports import write_report_files


def test_load_and_write_urls_round_trip(tmp_path) -> None:
    input_file = tmp_path / "raw.txt"
    output_file = tmp_path / "resolved.txt"
    input_file.write_text(
        "hello https://www.instagram.com/reel/BBB/?utm=x\n"
        "https://instagram.com/p/AAA\n",
        encoding="utf-8",
    )

    urls = load_urls_from_file(input_file)
    write_urls_to_file(urls, output_file)

    assert urls == [
        "https://www.instagram.com/p/AAA/",
        "https://www.instagram.com/reel/BBB/",
    ]
    assert output_file.read_text(encoding="utf-8") == (
        "https://www.instagram.com/p/AAA/\n"
        "https://www.instagram.com/reel/BBB/\n"
    )


def test_load_urls_from_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_urls_from_file(tmp_path / "missing.txt")


def test_empty_url_file_writes_empty_output(tmp_path) -> None:
    output_file = tmp_path / "empty.txt"

    write_urls_to_file([], output_file)

    assert output_file.read_text(encoding="utf-8") == ""


def test_write_report_files_serializes_json_and_csv(tmp_path) -> None:
    report = RunReport(
        command="download",
        items=[
            DownloadItemResult(
                url="https://www.instagram.com/reel/AAA/",
                source="input",
                status="downloaded",
                output_path="/tmp/AAA.mp4",
                description="A reel #test",
                tags=["test"],
                comments=[{"author": "alice", "text": "Nice!"}],
            ),
            DownloadItemResult(
                url="https://www.instagram.com/reel/BBB/",
                source="input",
                status="failed",
                error="boom",
            ),
        ],
    ).finish()

    json_path, csv_path = write_report_files(report, tmp_path)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["status_counts"] == {"downloaded": 1, "failed": 1}
    assert payload["total_urls"] == 2

    with csv_path.open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows == [
        {
            "url": "https://www.instagram.com/reel/AAA/",
            "source": "input",
            "status": "downloaded",
            "output_path": "/tmp/AAA.mp4",
            "description": "A reel #test",
            "tags": '["test"]',
            "comments": '[{"author": "alice", "text": "Nice!"}]',
            "error": "",
        },
        {
            "url": "https://www.instagram.com/reel/BBB/",
            "source": "input",
            "status": "failed",
            "output_path": "",
            "description": "",
            "tags": "[]",
            "comments": "[]",
            "error": "boom",
        },
    ]
