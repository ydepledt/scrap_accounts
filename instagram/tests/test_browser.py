from __future__ import annotations

from scrap_insta.browser import extract_visible_instagram_urls, scan_page_for_instagram_urls
from scrap_insta.models import ScrapeConfig


class FakeMouse:
    def __init__(self) -> None:
        self.wheels: list[tuple[int, int]] = []

    def wheel(self, delta_x: int, delta_y: int) -> None:
        self.wheels.append((delta_x, delta_y))


class FakePage:
    def __init__(self, batches: list[list[str]]) -> None:
        self.batches = batches
        self.calls = 0
        self.mouse = FakeMouse()
        self.waits: list[int] = []

    def evaluate(self, script: str) -> list[str]:
        index = min(self.calls, len(self.batches) - 1)
        self.calls += 1
        return self.batches[index]

    def wait_for_timeout(self, delay_ms: int) -> None:
        self.waits.append(delay_ms)


def test_extract_visible_instagram_urls_normalizes_page_links() -> None:
    page = FakePage(
        [
            [
                "https://instagram.com/reel/BBB?utm=1",
                "https://www.instagram.com/p/AAA/",
                "https://example.com/p/NOPE/",
            ]
        ]
    )

    assert extract_visible_instagram_urls(page) == [
        "https://www.instagram.com/p/AAA/",
        "https://www.instagram.com/reel/BBB/",
    ]


def test_scan_page_stops_after_idle_scrolls() -> None:
    page = FakePage(
        [
            ["https://www.instagram.com/reel/AAA/"],
            ["https://www.instagram.com/reel/AAA/"],
            ["https://www.instagram.com/reel/AAA/"],
            ["https://www.instagram.com/reel/BBB/"],
        ]
    )

    urls = scan_page_for_instagram_urls(
        page,
        ScrapeConfig(
            scrolls=10,
            scroll_delay_ms=50,
            scroll_pixels=100,
            stop_when_no_new=True,
            max_idle_scrolls=2,
            prompt_for_manual_navigation=False,
        ),
    )

    assert urls == ["https://www.instagram.com/reel/AAA/"]
    assert page.mouse.wheels == [(0, 100), (0, 100)]
    assert page.waits == [50, 50]


def test_scan_page_unlimited_scrolls_until_idle() -> None:
    page = FakePage(
        [
            ["https://www.instagram.com/reel/AAA/"],
            ["https://www.instagram.com/reel/BBB/"],
            ["https://www.instagram.com/reel/CCC/"],
            ["https://www.instagram.com/reel/CCC/"],
            ["https://www.instagram.com/reel/CCC/"],
        ]
    )

    urls = scan_page_for_instagram_urls(
        page,
        ScrapeConfig(
            scrolls=None,
            scroll_delay_ms=25,
            scroll_pixels=120,
            stop_when_no_new=True,
            max_idle_scrolls=2,
            prompt_for_manual_navigation=False,
        ),
    )

    assert urls == [
        "https://www.instagram.com/reel/AAA/",
        "https://www.instagram.com/reel/BBB/",
        "https://www.instagram.com/reel/CCC/",
    ]
    assert page.mouse.wheels == [(0, 120), (0, 120), (0, 120), (0, 120)]
    assert page.waits == [25, 25, 25, 25]


def test_scan_page_respects_limit() -> None:
    page = FakePage(
        [
            [
                "https://www.instagram.com/reel/BBB/",
                "https://www.instagram.com/reel/AAA/",
            ]
        ]
    )

    urls = scan_page_for_instagram_urls(
        page,
        ScrapeConfig(limit=1, prompt_for_manual_navigation=False),
    )

    assert urls == ["https://www.instagram.com/reel/AAA/"]
    assert page.mouse.wheels == []
