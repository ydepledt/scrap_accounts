# scrap-twitter

Personal CLI for backing up Twitter/X posts that are visible in your own browser session.

The tool uses the same shared scraper bricks as `scrap-insta`: platform URL rules, a Playwright visible-link scroller, and a `yt-dlp` downloader/report writer. It is meant for account-owned browser workflows such as Home, Likes, Bookmarks, profiles, search/explore timelines, or another Twitter/X page you navigate to manually.

## Install

```bash
python -m pip install -e .[dev]
python -m playwright install chromium
```

When running from this repository, `twitter/main.py` also adds `../common/src` to `sys.path` so the shared `scrap_common` package is available.

## Commands

Normalize pasted Twitter/X URLs:

```bash
scrap-twitter normalize --input raw_urls.txt --output resolved_twitter_urls.txt
```

Open a persistent browser profile, log in, and scrape a Twitter/X account page:

```bash
scrap-twitter scrape --source-page home --stop-when-no-new
scrap-twitter scrape --source-page likes --stop-when-no-new
scrap-twitter scrape --source-page bookmarks --stop-when-no-new
scrap-twitter scrape --source-page profile --username openai --stop-when-no-new
```

Use `--source-page manual --start-url URL` when you want to navigate yourself before scraping.

Download media or collect metadata:

```bash
scrap-twitter download --input scraped_twitter_urls.txt --comments-limit 100 --cookies-from-browser chrome
scrap-twitter download --input scraped_twitter_urls.txt --metadata-only --cookies-from-browser chrome
```

The JSON and CSV reports include URL, status, output path, media ID, text/title, tags, first N comments or replies when supported, and available `yt-dlp` stats such as `view_count`, `like_count`, `comment_count`, `reply_count`, `repost_count`, or `retweet_count`.

Run scrape plus download in one pass:

```bash
scrap-twitter backup --source-page bookmarks --metadata-only --comments-limit 50 --cookies-from-browser chrome --stop-when-no-new
```

## Notes

- Use this only for pages and content you can access legitimately in your browser.
- Twitter/X UI changes can affect visible-link scraping.
- Private likes and bookmarks usually need browser cookies for `yt-dlp`; use `--cookies-from-browser`.
