# scrap-insta

Personal CLI for backing up Instagram post, reel, and tv URLs that are visible in your own browser session.

The tool intentionally stays inside a manual, account-owned workflow: it scrapes visible DOM links from pages you open yourself, does not store passwords, and does not call private Instagram APIs.

## Install

```bash
python -m pip install -e .[dev]
python -m playwright install chromium
```

If you only want URL normalization or dry-run commands, the CLI can show help without Playwright or yt-dlp being importable.

Default paths, scraping values, download retries, and supported cookie browsers are
configured in `src/scrap_insta/config.toml`. Command-line options override these defaults.

## Commands

Normalize URLs from a pasted text file:

```bash
scrap-insta normalize --input raw_urls.txt --output resolved_instagram_urls.txt
```

Open a persistent browser profile, manually log in, navigate to Likes/Saved, then scrape visible links:

```bash
scrap-insta scrape --output scraped_instagram_urls.txt --stop-when-no-new
```

Keep scrolling without a fixed scroll count until repeated scrolls find no new URLs:

```bash
scrap-insta scrape --output scraped_instagram_urls.txt --stop-when-no-new --unlimited-scrolls
```

Download a normalized URL file:

```bash
scrap-insta download --input scraped_instagram_urls.txt --output-dir instagram_downloads --cookies-from-browser chrome
```

The download phase extracts each video's description, hashtags/tags, and the first
10 comments into the JSON and CSV reports. Change the number with
`--comments-limit N` (or `comments_limit` in `config.toml`), and use `0` to skip
comments:

```bash
scrap-insta download --input scraped_instagram_urls.txt --comments-limit 25 --cookies-from-browser chrome
```

Run the full manual backup flow:

```bash
scrap-insta backup --output-dir instagram_downloads --cookies-from-browser chrome --stop-when-no-new
```

Every download or backup run writes JSON and CSV reports with URL, source, status,
output path, description, tags, comments, and error details.

## Compatibility

Existing v0 entrypoints still work:

```bash
python main.py workaround --urls-file raw_urls.txt --download
python main.py browser-scrape --download
```

Both commands are deprecated aliases for the clearer `normalize`, `scrape`, `download`, and `backup` commands.

## Notes

- Use this only for content you can access legitimately in your browser.
- Instagram UI changes can affect visible-link scraping.
- `yt-dlp` support for Instagram may change over time; keep it updated if downloads start failing.
