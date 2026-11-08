from __future__ import annotations

import csv
import json
import sqlite3

from scrap_common.downloader import _media_file_paths, _metadata_for, _primary_media_info
from scrap_insta.ai_export import record_for_item, write_ai_export
from scrap_insta.archive import index_report, search_archive
from scrap_insta.cli import main
from scrap_insta.models import DownloadItemResult, RunReport
from scrap_insta.reports import read_report_file, write_report_files


def test_ai_record_preserves_rich_post_fields_without_cookie_leaks() -> None:
    extractor_info = {
        "title": "A hilarious gaming fail",
        "description": "Un clip de jeu #gaming #Humour",
        "uploader": "Alice Example",
        "uploader_id": "18273",
        "channel": "alice",
        "timestamp": 1762538400,
        "duration": 14.5,
        "thumbnail": "https://example.org/thumb.jpg",
        "width": 1080,
        "height": 1920,
        "http_headers": {"Cookie": "secret"},
        "session_id": "secret",
    }
    metadata = _metadata_for(extractor_info)
    assert "http_headers" not in metadata
    assert "session_id" not in metadata

    item = DownloadItemResult(
        url="https://www.instagram.com/reel/AAA/",
        source="input",
        status="downloaded",
        output_path="/files/AAA.mp4",
        description=extractor_info["description"],
        metadata=metadata,
        tags=["gaming", "Humour"],
        comments=[
            {"text": "Excellent", "like_count": 1, "author": "user_a"},
            {"text": "Je connais ce jeu !", "like_count": 20, "author": "user_b"},
        ],
        stats={"view_count": 17000, "like_count": 200, "comment_count": 200},
    )
    record = record_for_item(item, comments_limit=100)
    assert record["title"] == "A hilarious gaming fail"
    assert record["caption"] == "Un clip de jeu #gaming #Humour"
    assert record["hashtags"] == ["gaming", "humour"]
    assert record["author"]["username"] == "alice"
    assert record["published_at"] is not None
    assert record["engagement"]["views"] == 17000
    assert record["comments_retrieval"]["status"] == "partial_or_unverified"
    assert record["comments_retrieval"]["exhaustive"] is False
    assert record["ai_input"]["representative_comments"][0] == "Je connais ce jeu !"
    assert "user_b" not in json.dumps(record["ai_input"])
    assert "secret" not in json.dumps(record)


def test_ai_export_writes_one_record_per_url_and_csv_summary(tmp_path) -> None:
    report = RunReport(
        command="download",
        metadata={"comments_limit": 100},
        items=[
            DownloadItemResult(
                url="https://www.instagram.com/reel/AAA/",
                source="input",
                status="downloaded",
                metadata={"title": "Test", "description": "Bonjour #conseil", "channel": "creator"},
                comments=[{"text": "Très utile"}],
                stats={"comment_count": 20},
            ),
            DownloadItemResult(
                url="https://www.instagram.com/reel/BBB/",
                source="input",
                status="failed",
                error="login required",
                error_type="login_required",
            ),
        ],
    ).finish()
    jsonl_file, csv_file = write_ai_export(report, tmp_path)

    lines = jsonl_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first, second = [json.loads(line) for line in lines]
    assert first["comments"][0]["text"] == "Très utile"
    assert first["hashtags"] == ["conseil"]
    assert second["comments_retrieval"]["status"] == "unavailable"
    assert second["error_type"] == "login_required"
    with csv_file.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["comments_collected"] == "1"
    assert rows[1]["status"] == "failed"


def test_carousel_keeps_all_downloaded_media_paths() -> None:
    info = {
        "_type": "playlist",
        "id": "POST",
        "title": "Post title",
        "entries": [
            {
                "id": "videoA",
                "description": "Caption #jeu",
                "comments": [{"text": "First"}],
                "requested_downloads": [{"filepath": "/files/videoA.mp4"}],
            },
            {
                "id": "videoB",
                "requested_downloads": [{"filepath": "/files/videoB.mp4"}],
            },
        ],
    }
    class FakeDL:
        def prepare_filename(self, entry):
            return f"/files/{entry['id']}.mp4"

    primary = _primary_media_info(info)
    assert primary["description"] == "Caption #jeu"
    assert primary["comments"] == [{"text": "First"}]
    assert _media_file_paths(FakeDL(), info) == ["/files/videoA.mp4", "/files/videoB.mp4"]


def test_existing_report_can_be_exported_via_cli(tmp_path) -> None:
    report = RunReport(
        command="download",
        metadata={"comments_limit": 25},
        items=[
            DownloadItemResult(
                url="https://www.instagram.com/reel/AAA/",
                source="input",
                status="metadata",
                metadata={"title": "A title", "description": "A caption #jeu"},
            ),
        ],
    ).finish()
    json_path, _ = write_report_files(report, tmp_path)
    assert read_report_file(json_path).items[0].metadata["title"] == "A title"

    assert main(["export-ai", "--report", str(json_path)]) == 0
    record = json.loads((tmp_path / "analysis_ready.jsonl").read_text().splitlines()[0])
    assert record["title"] == "A title"
    assert record["comments_retrieval"]["status"] == "not_returned_by_extractor"


def test_archive_migrates_existing_database_and_indexes_title(tmp_path) -> None:
    db = tmp_path / "archive.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("""
            CREATE TABLE archive_items (
                url TEXT PRIMARY KEY, status TEXT NOT NULL, output_path TEXT,
                media_id TEXT, duplicate_of TEXT, description TEXT,
                tags_json TEXT NOT NULL, comments_json TEXT NOT NULL,
                first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
                last_downloaded TEXT, error_type TEXT, error TEXT
            )
        """)
    item = DownloadItemResult(
        url="https://www.instagram.com/reel/ABC/",
        source="input", status="downloaded",
        metadata={"title": "Funny game clip", "channel": "alice"},
        comments=[{"text": "jeu incroyable"}],
    )
    index_report(RunReport(command="download", items=[item]).finish(), db)
    matches = search_archive(db, query="Funny game")
    assert len(matches) == 1
    assert matches[0]["metadata"]["channel"] == "alice"

    # Failed refreshes must not erase previously indexed metadata and comments.
    failed = DownloadItemResult(url=item.url, source="input", status="failed", error="rate limit")
    index_report(RunReport(command="retry", items=[failed]).finish(), db)
    result = search_archive(db, query="Funny game")[0]
    assert result["metadata"]["title"] == "Funny game clip"
    assert result["comments"][0]["text"] == "jeu incroyable"
