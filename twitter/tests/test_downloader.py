from __future__ import annotations

from typing import Any

from scrap_twitter.downloader import download_urls
from scrap_twitter.models import DownloadConfig


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
        return {
            "id": "AAA11122233",
            "ext": "mp4",
            "uploader": "tester",
            "title": "A post",
            "tags": ["python"],
            "view_count": 123,
            "like_count": 45,
            "comment_count": 6,
            "repost_count": 7,
            "comments": [
                {"id": "1", "author": "alice", "text": "First!", "like_count": 2},
                {"id": "2", "author": "bob", "text": "Nice"},
            ],
        }

    def prepare_filename(self, info: dict[str, str]) -> str:
        return f"/downloads/{info['uploader']}_{info['id']}.{info['ext']}"


def test_download_urls_reports_comments_and_stats(tmp_path) -> None:
    FakeYoutubeDL.instances.clear()
    report = download_urls(
        DownloadConfig(
            urls=["https://twitter.com/OpenAI/status/1800000000000000000?s=20"],
            output_dir=tmp_path,
            comments_limit=1,
        ),
        twitter_dl_class=FakeYoutubeDL,
    )

    assert report.status_counts() == {"downloaded": 1}
    assert report.items[0].url == "https://x.com/openai/status/1800000000000000000/"
    assert report.items[0].comments == [
        {"id": "1", "author": "alice", "text": "First!", "like_count": 2}
    ]
    assert report.items[0].stats["view_count"] == 123
    assert report.items[0].stats["like_count"] == 45
    assert report.items[0].stats["repost_count"] == 7
    assert FakeYoutubeDL.instances[0].options["getcomments"] is True
    assert FakeYoutubeDL.instances[0].options["noplaylist"] is True
