from __future__ import annotations

from scrap_insta.archive import duplicate_groups, index_report, search_archive
from scrap_insta.models import DownloadItemResult, RunReport


def test_archive_indexes_reports_and_searches_items(tmp_path) -> None:
    db_path = tmp_path / "archive.sqlite3"
    report = RunReport(
        command="download",
        metadata={"run_id": "run-1"},
        items=[
            DownloadItemResult(
                url="https://www.instagram.com/reel/AAA/",
                source="input",
                status="downloaded",
                output_path="/downloads/a.mp4",
                media_id="media-1",
                description="A cooking clip #food",
                tags=["food"],
                comments=[{"author": "alice", "text": "tasty"}],
            ),
            DownloadItemResult(
                url="https://www.instagram.com/p/BBB/",
                source="input",
                status="failed",
                error_type="login_required",
                error="login required",
            ),
        ],
    ).finish()

    index_report(report, db_path)

    rows = search_archive(db_path, query="cooking", tag="food")
    assert len(rows) == 1
    assert rows[0]["url"] == "https://www.instagram.com/reel/AAA/"
    assert rows[0]["tags"] == ["food"]

    failed_rows = search_archive(db_path, status="failed")
    assert failed_rows[0]["error_type"] == "login_required"


def test_archive_duplicate_groups(tmp_path) -> None:
    db_path = tmp_path / "archive.sqlite3"
    report = RunReport(
        command="download",
        metadata={"run_id": "run-1"},
        items=[
            DownloadItemResult(
                url="https://www.instagram.com/reel/AAA/",
                source="input",
                status="downloaded",
                media_id="same-media",
            ),
            DownloadItemResult(
                url="https://www.instagram.com/p/BBB/",
                source="input",
                status="downloaded",
                media_id="same-media",
                duplicate_of="https://www.instagram.com/reel/AAA/",
            ),
        ],
    ).finish()

    index_report(report, db_path)

    assert duplicate_groups(db_path) == [
        {
            "duplicate_key": "same-media",
            "count": 2,
            "urls": [
                "https://www.instagram.com/reel/AAA/",
                "https://www.instagram.com/p/BBB/",
            ],
        }
    ]
