from __future__ import annotations

from scrap_twitter.urls import extract_urls_from_text, normalize_twitter_url


def test_normalize_twitter_video_urls() -> None:
    assert (
        normalize_twitter_url("https://twitter.com/OpenAI/status/1800000000000000000?s=20")
        == "https://x.com/openai/status/1800000000000000000/"
    )
    assert (
        normalize_twitter_url("https://x.com/i/status/1800000000000000001/video/1")
        == "https://x.com/i/status/1800000000000000001/"
    )


def test_normalize_twitter_url_rejects_unsupported_urls() -> None:
    assert normalize_twitter_url("https://x.com/home") is None
    assert normalize_twitter_url("https://example.com/openai/status/1") is None
    assert normalize_twitter_url("not-a-url") is None


def test_extract_urls_from_text_deduplicates_and_sorts() -> None:
    raw_text = """
    Tweet: https://twitter.com/OpenAI/status/1800000000000000002?s=20
    Duplicate: https://x.com/openai/status/1800000000000000002
    Media: https://mobile.x.com/AnthropicAI/status/1800000000000000003/photo/1
    Ignore: https://x.com/home
    """

    assert extract_urls_from_text(raw_text) == [
        "https://x.com/anthropicai/status/1800000000000000003/",
        "https://x.com/openai/status/1800000000000000002/",
    ]
