from __future__ import annotations

from scrap_insta.urls import extract_urls_from_text, normalize_instagram_url


def test_normalize_instagram_url_strips_tracking_and_forces_canonical_host() -> None:
    assert (
        normalize_instagram_url("http://m.instagram.com/reel/AbC_123-/?igsh=abc#frag")
        == "https://www.instagram.com/reel/AbC_123-/"
    )


def test_normalize_instagram_url_rejects_unsupported_urls() -> None:
    assert normalize_instagram_url("https://example.com/reel/AbC/") is None
    assert normalize_instagram_url("https://www.instagram.com/stories/user/1/") is None
    assert normalize_instagram_url("not-a-url") is None


def test_extract_urls_from_text_deduplicates_and_sorts() -> None:
    raw_text = """
    First: https://instagram.com/p/BBB?utm_source=x
    Duplicate: https://www.instagram.com/p/BBB/
    Reel: https://www.instagram.com/reel/AAA/
    Ignore: https://www.instagram.com/stories/person/1/
    TV: https://m.instagram.com/tv/CCC#comments
    """

    assert extract_urls_from_text(raw_text) == [
        "https://www.instagram.com/p/BBB/",
        "https://www.instagram.com/reel/AAA/",
        "https://www.instagram.com/tv/CCC/",
    ]
