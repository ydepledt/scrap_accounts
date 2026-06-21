from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if SRC_DIR.exists():
    sys.path.insert(0, str(SRC_DIR))

from scrap_insta import extract_urls_from_text, normalize_instagram_url
from scrap_insta.browser import extract_visible_instagram_urls, scrape_current_page_urls
from scrap_insta.cli import build_argument_parser, main
from scrap_insta.downloader import download_instagram_urls
from scrap_insta.files import load_urls_from_file, write_urls_to_file


if __name__ == "__main__":
    raise SystemExit(main())
