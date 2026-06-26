from __future__ import annotations

from typing import Any

from scrap_insta.downloader import download_urls
from scrap_insta.models import DownloadConfig


class FakeYoutubeDL:
    instances: list["FakeYoutubeDL"] = []

    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options
        self.__class__.instances.append(self)

    def __enter__(self) -> "FakeYoutubeDL":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def extract_info(self, url: str, download: bool) -> dict[str, Any]:
        if "FAIL" in url:
            raise RuntimeError("download boom")
        code = url.rstrip("/").rsplit("/", 1)[-1]
        return {
            "id": code,
            "ext": "mp4",
            "uploader": "tester",
            "description": "A test reel #python #scraping",
            "tags": ["video", "python"],
            "comments": [
                {"id": "1", "author": "alice", "text": "First!", "like_count": 2},
                {"id": "2", "author": "bob", "text": "Nice reel"},
                {"id": "3", "author": "eve", "text": "Third"},
            ],
        }

    def prepare_filename(self, info: dict[str, str]) -> str:
        return f"/downloads/{info['uploader']}_{info['id']}.{info['ext']}"


def test_download_urls_uses_injected_downloader_and_reports_results(tmp_path) -> None:
    FakeYoutubeDL.instances.clear()
    report = download_urls(
        DownloadConfig(
            urls=[
                "https://www.instagram.com/reel/AAA/",
                "https://www.instagram.com/reel/FAIL/",
                "not-a-url",
            ],
            output_dir=tmp_path,
            cookies_from_browser="chrome",
            retries=7,
            comments_limit=2,
        ),
        youtube_dl_class=FakeYoutubeDL,
    )

    assert report.status_counts() == {"failed": 2, "downloaded": 1}
    assert report.items[0].url == "not-a-url"
    assert report.items[0].status == "failed"
    assert report.items[0].error_type == "invalid_url"
    assert report.items[1].output_path == "/downloads/tester_AAA.mp4"
    assert report.items[1].description == "A test reel #python #scraping"
    assert report.items[1].tags == ["video", "python", "scraping"]
    assert report.items[1].comments == [
        {"id": "1", "author": "alice", "text": "First!", "like_count": 2},
        {"id": "2", "author": "bob", "text": "Nice reel"},
    ]
    assert FakeYoutubeDL.instances[0].options["cookiesfrombrowser"] == ("chrome",)
    assert FakeYoutubeDL.instances[0].options["retries"] == 7
    assert FakeYoutubeDL.instances[0].options["getcomments"] is True


def test_download_urls_dry_run_does_not_require_ytdlp(tmp_path) -> None:
    report = download_urls(
        DownloadConfig(
            urls=["https://instagram.com/p/AAA?utm=1", "bad"],
            output_dir=tmp_path,
            dry_run=True,
        )
    )

    assert report.status_counts() == {"failed": 1, "dry_run": 1}
    assert report.items[1].url == "https://www.instagram.com/p/AAA/"


def test_download_urls_can_disable_comment_extraction(tmp_path) -> None:
    FakeYoutubeDL.instances.clear()
    report = download_urls(
        DownloadConfig(
            urls=["https://www.instagram.com/reel/AAA/"],
            output_dir=tmp_path,
            comments_limit=0,
        ),
        youtube_dl_class=FakeYoutubeDL,
    )

    assert report.items[0].comments == []
    assert FakeYoutubeDL.instances[0].options["getcomments"] is False


def test_download_urls_supports_metadata_only_and_media_options(tmp_path) -> None:
    FakeYoutubeDL.instances.clear()
    report = download_urls(
        DownloadConfig(
            urls=["https://www.instagram.com/reel/AAA/"],
            output_dir=tmp_path,
            format_selector="best",
            audio_only=True,
            write_thumbnail=True,
            metadata_only=True,
        ),
        youtube_dl_class=FakeYoutubeDL,
    )

    assert report.status_counts() == {"metadata": 1}
    assert report.items[0].output_path is None
    options = FakeYoutubeDL.instances[0].options
    assert options["format"] == "best"
    assert options["skip_download"] is True
    assert options["writethumbnail"] is True
    assert options["postprocessors"][0]["key"] == "FFmpegExtractAudio"
