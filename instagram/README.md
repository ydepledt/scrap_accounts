# scrap-insta

Personal CLI for backing up Instagram post, reel, and tv URLs that are visible in your own browser session.

The tool intentionally stays inside a manual, account-owned workflow: it scrapes visible DOM links from pages you open yourself, does not store passwords, and does not call private Instagram APIs.

## Install

```bash
python -m pip install -e .[dev]
python -m playwright install chromium
```

If you only want URL normalization or dry-run commands, the CLI can show help without Playwright or yt-dlp being importable.

Default paths, scraping values, download retries, media options, run history,
archive indexing, and supported cookie browsers are configured in
`src/scrap_insta/config.toml`. Command-line options override these defaults.
Use `--config custom.toml` before or after a subcommand to load a different config file.

## Commands

Normalize URLs from a pasted text file:

```bash
scrap-insta normalize --input raw_urls.txt --output resolved_instagram_urls.txt
```

Check the local setup:

```bash
scrap-insta doctor --cookies-from-browser chrome
```

Open a persistent browser profile, manually log in, navigate to Likes/Saved, then scrape visible links:

```bash
scrap-insta scrape --output scraped_instagram_urls.txt --stop-when-no-new
```

Keep scrolling without a fixed scroll count until repeated scrolls find no new URLs:

```bash
scrap-insta scrape --output scraped_instagram_urls.txt --stop-when-no-new --unlimited-scrolls
```

Merge newly scraped URLs into an existing URL file:

```bash
scrap-insta scrape --output scraped_instagram_urls.txt --append --stop-when-no-new
```

Download a normalized URL file:

```bash
scrap-insta download --input scraped_instagram_urls.txt --output-dir instagram_downloads --cookies-from-browser chrome
```

The download phase extracts each video's description, hashtags/tags, and the configured
number of comments into the JSON and CSV reports. Change the number with
`--comments-limit N` (or `comments_limit` in `config.toml`), and use `0` to skip
comments:

```bash
scrap-insta download --input scraped_instagram_urls.txt --comments-limit 25 --cookies-from-browser chrome
```

Collect metadata without downloading media:

```bash
scrap-insta download --input scraped_instagram_urls.txt --metadata-only --cookies-from-browser chrome
```

Control yt-dlp output:

```bash
scrap-insta download --input scraped_instagram_urls.txt --format "bestvideo+bestaudio/best" --write-thumbnail
scrap-insta download --input scraped_instagram_urls.txt --audio-only
```

Run the full manual backup flow:

```bash
scrap-insta backup --output-dir instagram_downloads --cookies-from-browser chrome --stop-when-no-new
```

Every download or backup run writes JSON and CSV reports with URL, source, status,
output path, media ID, duplicate source URL, description, tags, comments, error
type, and error details.

Report-producing commands also update `archive.sqlite3` and write a timestamped
history copy under `runs/RUN_ID/` by default. Disable those side effects with
`--no-index` or `--no-run-history`:

```bash
scrap-insta download --input scraped_instagram_urls.txt --no-index --no-run-history
```

Retry failed URLs from a previous report:

```bash
scrap-insta retry --report instagram_downloads/download_report.json --cookies-from-browser chrome
```

Summarize a report:

```bash
scrap-insta summary --report instagram_downloads/download_report.json
```

Create a local HTML gallery from a report:

```bash
scrap-insta gallery --report instagram_downloads/download_report.json --output instagram_downloads/index.html
```

Compare two URL files:

```bash
scrap-insta diff --old previous_urls.txt --new scraped_instagram_urls.txt
```

Search the archive index:

```bash
scrap-insta search --query "vacation"
scrap-insta search --tag travel --status downloaded
```

List duplicate media groups:

```bash
scrap-insta search --duplicates
```

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

## AI-ready exports: captions, metadata, comments and media

Each `download`, `backup`, or `retry` run now writes alongside the normal reports:

- `analysis_ready.jsonl`: **one JSON object per input URL** with title, caption,
  hashtags, creator, publication date, video properties, cover, engagement,
  available comments, and local media file paths (including carousels).
- `analysis_ready.csv`: readable summary with comment coverage and useful fields.
- The same files are preserved per run under `runs/<run_id>/` by default.

`ai_input` contains the caption, title, hashtags and up to 30 representative
comment texts. It is a starting point for a future classifier such as
*humour*, *conseils*, *jeux vidéo*, *autre*. The `media.local_files` paths let
a multimodal model inspect the video/audio, which is important when the joke
or advice is not described in the caption. **No AI API call is made by this project.**

Download up to 100 available comments per publication and keep the thumbnail:

```bash
scrap-insta download --input urls.txt --output-dir instagram_downloads \
  --cookies-from-browser chrome --comments-limit 100 --write-thumbnail
```

Collect only text/metadata and whatever comments the extractor exposes:

```bash
scrap-insta download --input urls.txt --metadata-only \
  --comments-limit 100 --cookies-from-browser chrome
```

Re-export a saved report without touching Instagram again:

```bash
scrap-insta export-ai --report instagram_downloads/download_report.json
```

The `comments_retrieval.status` value distinguishes disabled, unavailable,
limit reached, partial/unverified, zero reported, and not returned by the
extractor. **Requesting N comments does not guarantee N comments**, and the
`exhaustive` flag is deliberately false. Instagram may restrict pages,
return partial metadata, or invalidate cookies. Never invent missing values.

For a URL list, use **individual post/reel/tv links**, not account homepage
URLs. Posts visible in an authenticated browser can still be discovered using
the existing `scrape` flow. Review any personal information in comments
before sending a dataset to an external AI service.
