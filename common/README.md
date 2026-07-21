# scrap-common

Shared object-oriented bricks used by the platform scrapers.

This package intentionally contains platform-neutral code:

- `PlatformUrlRules` for URL normalization, text extraction, and visible-link JavaScript.
- `VisibleLinkScraper` for Playwright-based browser scrolling and DOM link collection.
- `YtDlpMediaDownloader` for `yt-dlp` downloads, metadata, comments, and stats extraction.
- Shared run report and item result dataclasses.

Platform packages such as `instagram/` and `youtube/` should provide only their URL rules, defaults, CLI surface, and any platform-specific presentation.
