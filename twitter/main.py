from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
COMMON_SRC_DIR = PROJECT_ROOT.parent / "common" / "src"

for path in (SRC_DIR, COMMON_SRC_DIR):
    if path.exists():
        sys.path.insert(0, str(path))

from scrap_twitter import extract_urls_from_text, normalize_twitter_url
from scrap_twitter.browser import extract_visible_twitter_urls, scrape_current_page_urls
from scrap_twitter.cli import build_argument_parser, main
from scrap_twitter.downloader import download_twitter_urls
from scrap_twitter.files import load_urls_from_file, write_urls_to_file


if __name__ == "__main__":
    raise SystemExit(main())
