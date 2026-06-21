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

    def extract_info(self, url: str, download: bool) -> dict[str, str]:
        if "FAIL" in url:
            raise RuntimeError("download boom")
        code = url.rstrip("/").rsplit("/", 1)[-1]
        return {"id": code, "ext": "mp4", "uploader": "tester"}

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
        ),
        youtube_dl_class=FakeYoutubeDL,
    )

    assert report.status_counts() == {"failed": 2, "downloaded": 1}
    assert report.items[0].url == "not-a-url"
    assert report.items[0].status == "failed"
    assert report.items[1].output_path == "/downloads/tester_AAA.mp4"
    assert FakeYoutubeDL.instances[0].options["cookiesfrombrowser"] == ("chrome",)
    assert FakeYoutubeDL.instances[0].options["retries"] == 7


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
