from __future__ import annotations

from pathlib import Path

from saved_links import filter_saved_urls, load_saved_urls, pick_saved_urls, saved_url_file


def test_load_saved_links_from_existing_library_without_rewriting(tmp_path: Path) -> None:
    path = saved_url_file(tmp_path, "Instagram")
    path.parent.mkdir()
    original = (
        "https://www.instagram.com/reel/AAA/\n"
        "https://www.instagram.com/p/BBB/\n"
        "https://www.instagram.com/reel/AAA/\n"
        "https://malicious.example/reel/CCC/\n"
        "not-an-url\n"
    )
    path.write_text(original, encoding="utf-8")
    assert load_saved_urls(path, "Instagram") == [
        "https://www.instagram.com/reel/AAA/",
        "https://www.instagram.com/p/BBB/",
    ]
    assert path.read_text(encoding="utf-8") == original


def test_filter_and_select_from_filtered_urls(tmp_path: Path) -> None:
    urls = [
        "https://www.instagram.com/reel/ABC/",
        "https://www.instagram.com/p/DEF/",
        "https://www.instagram.com/reel/GHI/",
    ]
    visible = filter_saved_urls(urls, "reel")
    assert visible == [urls[0], urls[2]]
    assert pick_saved_urls(visible, (1, 0, 1, 99)) == [urls[0], urls[2]]
    assert pick_saved_urls(visible, ()) == []


def test_empty_list_and_platform_guard(tmp_path: Path) -> None:
    assert load_saved_urls(saved_url_file(tmp_path, "YouTube"), "YouTube") == []
    try:
        saved_url_file(tmp_path, "../escape")
        assert False, "Expected ValueError"
    except ValueError:
        pass
