from __future__ import annotations

from scrap_youtube.urls import extract_urls_from_text, normalize_youtube_url


def test_normalize_youtube_video_urls() -> None:
    assert (
        normalize_youtube_url("https://m.youtube.com/watch?v=AbC_123-45&utm=1")
        == "https://www.youtube.com/watch?v=AbC_123-45"
    )
    assert (
        normalize_youtube_url("https://youtu.be/AbC_123-45?t=12")
        == "https://www.youtube.com/watch?v=AbC_123-45"
    )


def test_normalize_youtube_playlist_and_shorts_urls() -> None:
    assert (
        normalize_youtube_url("https://youtube.com/playlist?list=LL&feature=share")
        == "https://www.youtube.com/playlist?list=LL"
    )
    assert (
        normalize_youtube_url("https://www.youtube.com/shorts/AbC_123-45?feature=share")
        == "https://www.youtube.com/shorts/AbC_123-45/"
    )


def test_extract_urls_from_text_deduplicates_and_sorts() -> None:
    raw_text = """
    Watch: https://youtube.com/watch?v=BBB11122233&utm=1
    Duplicate: https://www.youtube.com/watch?v=BBB11122233
    Short: https://www.youtube.com/shorts/AAA11122233
    Playlist: https://www.youtube.com/playlist?list=PL123
    Ignore: https://www.youtube.com/feed/history
    """

    assert extract_urls_from_text(raw_text) == [
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/shorts/AAA11122233/",
        "https://www.youtube.com/watch?v=BBB11122233",
    ]
