from __future__ import annotations

import csv
import json

import pytest

from scrap_insta.files import (
    diff_url_files,
    load_urls_from_file,
    merge_url_lists,
    write_urls_to_file,
)
from scrap_insta.gallery import write_html_gallery
from scrap_insta.models import DownloadItemResult, RunReport
from scrap_insta.reports import read_report_file, summarize_report, write_report_files


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


def test_merge_and_diff_url_lists(tmp_path) -> None:
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"
    old_file.write_text(
        "https://instagram.com/p/AAA\nhttps://instagram.com/reel/BBB\n",
        encoding="utf-8",
    )
    new_file.write_text(
        "https://instagram.com/reel/BBB\nhttps://instagram.com/tv/CCC\n",
        encoding="utf-8",
    )

    assert merge_url_lists(load_urls_from_file(old_file), load_urls_from_file(new_file)) == [
        "https://www.instagram.com/p/AAA/",
        "https://www.instagram.com/reel/BBB/",
        "https://www.instagram.com/tv/CCC/",
    ]
    assert diff_url_files(old_file, new_file) == {
        "added": ["https://www.instagram.com/tv/CCC/"],
        "removed": ["https://www.instagram.com/p/AAA/"],
        "shared": ["https://www.instagram.com/reel/BBB/"],
    }


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
            "error_type": "",
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
            "error_type": "",
            "error": "boom",
        },
    ]

    loaded_report = read_report_file(json_path)
    assert loaded_report.status_counts() == {"downloaded": 1, "failed": 1}

    summary = summarize_report(loaded_report)
    assert summary["top_tags"] == [("test", 1)]
    assert summary["failed_urls"] == ["https://www.instagram.com/reel/BBB/"]


def test_write_html_gallery(tmp_path) -> None:
    media_file = tmp_path / "clip.mp4"
    media_file.write_text("placeholder", encoding="utf-8")
    report = RunReport(
        command="download",
        items=[
            DownloadItemResult(
                url="https://www.instagram.com/reel/AAA/",
                source="input",
                status="downloaded",
                output_path=str(media_file),
                description="Saved clip",
                tags=["fun"],
            )
        ],
    ).finish()

    output_file = tmp_path / "index.html"
    write_html_gallery(report, output_file)

    html = output_file.read_text(encoding="utf-8")
    assert "Instagram Backup Gallery" in html
    assert '<video src="clip.mp4"' in html
    assert "#fun" in html
