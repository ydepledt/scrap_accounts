# scrap-youtube

Personal CLI for backing up YouTube videos, shorts, and playlists that are visible in your own browser session.

The tool uses the same shared scraper bricks as `scrap-insta`: platform URL rules, a Playwright visible-link scroller, and a `yt-dlp` downloader/report writer. It is meant for account-owned browser workflows such as History, Liked videos, Playlists, or another YouTube page you navigate to manually.

## Install

```bash
python -m pip install -e .[dev]
python -m playwright install chromium
```

When running from this repository, `youtube/main.py` also adds `../common/src` to `sys.path` so the shared `scrap_common` package is available.

## Commands

Normalize pasted YouTube URLs:

```bash
scrap-youtube normalize --input raw_urls.txt --output resolved_youtube_urls.txt
```

Open a persistent browser profile, log in, and scrape a YouTube account page:

```bash
scrap-youtube scrape --source-page history --stop-when-no-new
scrap-youtube scrape --source-page liked-videos --stop-when-no-new
scrap-youtube scrape --source-page playlists --stop-when-no-new
```

Use `--source-page manual --start-url URL` when you want to navigate yourself before scraping.

Download videos or collect metadata:

```bash
scrap-youtube download --input scraped_youtube_urls.txt --comments-limit 100 --cookies-from-browser chrome
scrap-youtube download --input scraped_youtube_urls.txt --metadata-only --include-playlists --cookies-from-browser chrome
```

The JSON and CSV reports include URL, status, output path, media ID, title/description, tags, first N comments, and available `yt-dlp` stats such as `view_count`, `like_count`, `comment_count`, channel, and playlist fields.

Run scrape plus download in one pass:

```bash
scrap-youtube backup --source-page history --metadata-only --comments-limit 50 --cookies-from-browser chrome --stop-when-no-new
```

## Notes

- Use this only for pages and content you can access legitimately in your browser.
- YouTube UI changes can affect visible-link scraping.
- Private history and liked videos usually need browser cookies for `yt-dlp`; use `--cookies-from-browser`.
