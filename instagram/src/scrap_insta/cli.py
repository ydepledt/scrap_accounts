from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from .browser import scrape_visible_urls
from .constants import (
    COOKIE_BROWSER_CHOICES,
    DEFAULT_MAX_IDLE_SCROLLS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROFILE_DIR,
    DEFAULT_RESOLVED_URLS_OUTPUT,
    DEFAULT_RETRIES,
    DEFAULT_SCROLL_DELAY_MS,
    DEFAULT_SCROLL_PIXELS,
    DEFAULT_SCROLLS,
    DEFAULT_URLS_OUTPUT,
    INSTAGRAM_LOGIN_URL,
)
from .downloader import download_urls
from .files import load_urls_from_file, write_urls_to_file
from .models import DownloadConfig, ScrapeConfig
from .reports import write_report_files

LOGGER = logging.getLogger(__name__)


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _add_cookie_options(parser: argparse.ArgumentParser) -> None:
    cookie_group = parser.add_mutually_exclusive_group()
    cookie_group.add_argument(
        "--cookies-from-browser",
        choices=COOKIE_BROWSER_CHOICES,
        default=None,
        help="Read yt-dlp cookies from a logged-in browser profile.",
    )
    cookie_group.add_argument(
        "--cookies-file",
        default=None,
        type=Path,
        help="Read yt-dlp cookies from a Netscape-format cookies.txt file.",
    )


def _add_download_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help="Directory where downloaded media and archives are written.",
    )
    _add_cookie_options(parser)
    parser.add_argument(
        "--archive-file",
        default=None,
        type=Path,
        help="yt-dlp download archive file. Defaults to OUTPUT_DIR/downloaded_archive.txt.",
    )
    parser.add_argument(
        "--retries",
        default=DEFAULT_RETRIES,
        type=non_negative_int,
        help="Number of yt-dlp retries per URL.",
    )
    parser.add_argument(
        "--overwrite",
        dest="skip_existing",
        action="store_false",
        help="Allow yt-dlp to overwrite existing files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report URLs without importing yt-dlp or downloading files.",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        type=Path,
        help="Directory for JSON and CSV run reports. Defaults to OUTPUT_DIR.",
    )
    parser.set_defaults(skip_existing=True)


def _add_scrape_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--start-url",
        default=INSTAGRAM_LOGIN_URL,
        help="Page opened before manual navigation.",
    )
    parser.add_argument(
        "--profile-dir",
        default=DEFAULT_PROFILE_DIR,
        type=Path,
        help="Local persistent Playwright profile directory.",
    )
    parser.add_argument(
        "--scrolls",
        default=DEFAULT_SCROLLS,
        type=non_negative_int,
        help="Number of scroll gestures to perform.",
    )
    parser.add_argument(
        "--unlimited-scrolls",
        action="store_true",
        help="Keep scrolling until --stop-when-no-new or --limit stops the scrape.",
    )
    parser.add_argument(
        "--scroll-delay-ms",
        default=DEFAULT_SCROLL_DELAY_MS,
        type=non_negative_int,
        help="Delay after each scroll.",
    )
    parser.add_argument(
        "--scroll-pixels",
        default=DEFAULT_SCROLL_PIXELS,
        type=positive_int,
        help="Vertical pixels per scroll gesture.",
    )
    parser.add_argument(
        "--limit",
        default=None,
        type=positive_int,
        help="Stop after collecting this many URLs.",
    )
    parser.add_argument(
        "--max-idle-scrolls",
        default=DEFAULT_MAX_IDLE_SCROLLS,
        type=positive_int,
        help="Idle scrolls allowed before stopping when --stop-when-no-new is set.",
    )
    parser.add_argument(
        "--stop-when-no-new",
        action="store_true",
        help="Stop early after repeated scrolls find no new URLs.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless. Usually not useful for manual login.",
    )


def _scrape_config_from_args(args: argparse.Namespace) -> ScrapeConfig:
    return ScrapeConfig(
        start_url=args.start_url,
        profile_dir=args.profile_dir,
        scrolls=None if args.unlimited_scrolls else args.scrolls,
        scroll_delay_ms=args.scroll_delay_ms,
        scroll_pixels=args.scroll_pixels,
        limit=args.limit,
        max_idle_scrolls=args.max_idle_scrolls,
        stop_when_no_new=args.stop_when_no_new,
        headless=args.headless,
    )


def _download_config_from_args(
    args: argparse.Namespace,
    urls: list[str],
    command: str,
    source: str,
) -> DownloadConfig:
    return DownloadConfig(
        urls=urls,
        output_dir=args.output_dir,
        cookies_from_browser=args.cookies_from_browser,
        cookies_file=args.cookies_file,
        archive_file=args.archive_file,
        retries=args.retries,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        command=command,
        source=source,
    )


def _write_download_reports(args: argparse.Namespace, report) -> tuple[Path, Path]:
    report_dir = args.report_dir or args.output_dir
    json_path, csv_path = write_report_files(report, report_dir)
    LOGGER.info("Report written: %s", json_path)
    LOGGER.info("Report written: %s", csv_path)
    return json_path, csv_path


def run_normalize_command(args: argparse.Namespace) -> int:
    urls = load_urls_from_file(args.input)
    write_urls_to_file(urls, args.output)
    LOGGER.info("Normalized URLs: %s", len(urls))
    LOGGER.info("File written: %s", args.output)
    return 0


def run_scrape_command(args: argparse.Namespace) -> int:
    urls = scrape_visible_urls(_scrape_config_from_args(args))
    write_urls_to_file(urls, args.output)
    LOGGER.info("Scraped URLs: %s", len(urls))
    LOGGER.info("File written: %s", args.output)
    return 0


def run_download_command(args: argparse.Namespace) -> int:
    urls = load_urls_from_file(args.input)
    report = download_urls(_download_config_from_args(args, urls, "download", "input"))
    _write_download_reports(args, report)
    LOGGER.info("Status counts: %s", report.status_counts())
    return 1 if report.failed_count else 0


def run_backup_command(args: argparse.Namespace) -> int:
    scraped_urls = scrape_visible_urls(_scrape_config_from_args(args))
    urls_output = args.urls_output or args.output_dir / DEFAULT_URLS_OUTPUT
    write_urls_to_file(scraped_urls, urls_output)
    LOGGER.info("Scraped URLs: %s", len(scraped_urls))
    LOGGER.info("URL file written: %s", urls_output)

    report = download_urls(_download_config_from_args(args, scraped_urls, "backup", "scrape"))
    report.metadata["urls_output"] = str(urls_output)
    _write_download_reports(args, report)
    LOGGER.info("Status counts: %s", report.status_counts())
    return 1 if report.failed_count else 0


def run_workaround_command(args: argparse.Namespace) -> int:
    LOGGER.warning("`workaround` is deprecated; use `normalize` and `download` instead.")
    urls = load_urls_from_file(args.urls_file)
    write_urls_to_file(urls, args.resolved_urls_file)
    LOGGER.info("Normalized URLs: %s", len(urls))
    LOGGER.info("File written: %s", args.resolved_urls_file)

    if not args.download:
        return 0

    report = download_urls(_download_config_from_args(args, urls, "workaround", "input"))
    _write_download_reports(args, report)
    LOGGER.info("Status counts: %s", report.status_counts())
    return 1 if report.failed_count else 0


def run_browser_scrape_command(args: argparse.Namespace) -> int:
    LOGGER.warning("`browser-scrape` is deprecated; use `scrape` or `backup` instead.")
    args.output = args.urls_output
    urls = scrape_visible_urls(_scrape_config_from_args(args))
    write_urls_to_file(urls, args.urls_output)
    LOGGER.info("Scraped URLs: %s", len(urls))
    LOGGER.info("File written: %s", args.urls_output)

    if not args.download:
        return 0

    report = download_urls(_download_config_from_args(args, urls, "browser-scrape", "scrape"))
    _write_download_reports(args, report)
    LOGGER.info("Status counts: %s", report.status_counts())
    return 1 if report.failed_count else 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Back up visible Instagram reel/post/tv URLs from your own browser session."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser(
        "normalize",
        help="Normalize and deduplicate URLs from a text file.",
    )
    normalize_parser.add_argument("--input", required=True, type=Path, help="Input text file.")
    normalize_parser.add_argument(
        "--output",
        default=DEFAULT_RESOLVED_URLS_OUTPUT,
        type=Path,
        help="Normalized URL output file.",
    )
    normalize_parser.set_defaults(func=run_normalize_command)

    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Open a browser, let you navigate manually, then scrape visible URLs.",
    )
    scrape_parser.add_argument(
        "--output",
        default=DEFAULT_URLS_OUTPUT,
        type=Path,
        help="Scraped URL output file.",
    )
    _add_scrape_options(scrape_parser)
    scrape_parser.set_defaults(func=run_scrape_command)

    download_parser = subparsers.add_parser(
        "download",
        help="Download URLs from a text file with yt-dlp.",
    )
    download_parser.add_argument("--input", required=True, type=Path, help="Input URL file.")
    _add_download_options(download_parser)
    download_parser.set_defaults(func=run_download_command)

    backup_parser = subparsers.add_parser(
        "backup",
        help="Scrape visible URLs, save them, download them, and write reports.",
    )
    _add_scrape_options(backup_parser)
    _add_download_options(backup_parser)
    backup_parser.add_argument(
        "--urls-output",
        default=None,
        type=Path,
        help="Scraped URL file. Defaults to OUTPUT_DIR/scraped_instagram_urls.txt.",
    )
    backup_parser.set_defaults(func=run_backup_command)

    workaround_parser = subparsers.add_parser(
        "workaround",
        help="Deprecated alias: normalize a URL file and optionally download it.",
    )
    workaround_parser.add_argument("--urls-file", required=True, type=Path, help="Input URL file.")
    workaround_parser.add_argument(
        "--resolved-urls-file",
        default=DEFAULT_RESOLVED_URLS_OUTPUT,
        type=Path,
        help="Normalized URL output file.",
    )
    _add_download_options(workaround_parser)
    workaround_parser.add_argument(
        "--download",
        action="store_true",
        help="Download after normalization.",
    )
    workaround_parser.set_defaults(func=run_workaround_command)

    browser_parser = subparsers.add_parser(
        "browser-scrape",
        help="Deprecated alias: scrape visible URLs and optionally download them.",
    )
    browser_parser.add_argument(
        "--urls-output",
        default=DEFAULT_URLS_OUTPUT,
        type=Path,
        help="Scraped URL output file.",
    )
    _add_scrape_options(browser_parser)
    _add_download_options(browser_parser)
    browser_parser.add_argument(
        "--download",
        action="store_true",
        help="Download after scraping.",
    )
    browser_parser.set_defaults(func=run_browser_scrape_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        LOGGER.error("Interrupted.")
        return 130
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
