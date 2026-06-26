from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from .browser import scrape_visible_urls
from .config import CONFIG, AppConfig, load_config
from .downloader import download_urls
from .files import diff_url_files, load_urls_from_file, merge_url_lists, write_urls_to_file
from .gallery import write_html_gallery
from .models import DownloadConfig, ScrapeConfig
from .reports import (
    failed_urls_from_report,
    read_report_file,
    summarize_report,
    write_report_files,
)

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


def _app_config(args: argparse.Namespace) -> AppConfig:
    return getattr(args, "app_config", CONFIG)


def _add_cookie_options(parser: argparse.ArgumentParser, config: AppConfig) -> None:
    cookie_group = parser.add_mutually_exclusive_group()
    cookie_group.add_argument(
        "--cookies-from-browser",
        choices=config.cookie_browser_choices,
        default=None,
        help="Read yt-dlp cookies from a logged-in browser profile.",
    )
    cookie_group.add_argument(
        "--cookies-file",
        default=None,
        type=Path,
        help="Read yt-dlp cookies from a Netscape-format cookies.txt file.",
    )


def _add_download_options(
    parser: argparse.ArgumentParser,
    config: AppConfig,
    use_config_output_dir: bool = True,
) -> None:
    parser.add_argument(
        "--output-dir",
        default=config.output_dir if use_config_output_dir else None,
        type=Path,
        help="Directory where downloaded media and archives are written.",
    )
    _add_cookie_options(parser, config)
    parser.add_argument(
        "--archive-file",
        default=None,
        type=Path,
        help="yt-dlp download archive file. Defaults to OUTPUT_DIR/downloaded_archive.txt.",
    )
    parser.add_argument(
        "--retries",
        default=CONFIG.retries,
        type=non_negative_int,
        help="Number of yt-dlp retries per URL.",
    )
    parser.add_argument(
        "--comments-limit",
        default=CONFIG.comments_limit,
        type=non_negative_int,
        help="Extract the first N comments per video; use 0 to disable.",
    )
    parser.add_argument(
        "--format",
        dest="format_selector",
        default=config.format_selector,
        help="yt-dlp format selector, for example `bestvideo+bestaudio/best`.",
    )
    parser.add_argument(
        "--audio-only",
        action=argparse.BooleanOptionalAction,
        default=config.audio_only,
        help="Download audio only and extract it as mp3.",
    )
    parser.add_argument(
        "--write-thumbnail",
        action=argparse.BooleanOptionalAction,
        default=config.write_thumbnail,
        help="Ask yt-dlp to write the media thumbnail.",
    )
    parser.add_argument(
        "--metadata-only",
        action=argparse.BooleanOptionalAction,
        default=config.metadata_only,
        help="Extract metadata, tags, and comments without downloading media.",
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


def _add_scrape_options(parser: argparse.ArgumentParser, config: AppConfig) -> None:
    parser.add_argument(
        "--start-url",
        default=config.instagram_login_url,
        help="Page opened before manual navigation.",
    )
    parser.add_argument(
        "--profile-dir",
        default=config.profile_dir,
        type=Path,
        help="Local persistent Playwright profile directory.",
    )
    parser.add_argument(
        "--scrolls",
        default=config.scrolls,
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
        default=config.scroll_delay_ms,
        type=non_negative_int,
        help="Delay after each scroll.",
    )
    parser.add_argument(
        "--scroll-pixels",
        default=config.scroll_pixels,
        type=positive_int,
        help="Vertical pixels per scroll gesture.",
    )
    parser.add_argument(
        "--browser-width",
        default=config.browser_width,
        type=positive_int,
        help="Browser viewport width in pixels.",
    )
    parser.add_argument(
        "--browser-height",
        default=config.browser_height,
        type=positive_int,
        help="Browser viewport height in pixels.",
    )
    parser.add_argument(
        "--limit",
        default=None,
        type=positive_int,
        help="Stop after collecting this many URLs.",
    )
    parser.add_argument(
        "--max-idle-scrolls",
        default=CONFIG.max_idle_scrolls,
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
        browser_width=args.browser_width,
        browser_height=args.browser_height,
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
        comments_limit=args.comments_limit,
        format_selector=args.format_selector,
        audio_only=args.audio_only,
        write_thumbnail=args.write_thumbnail,
        metadata_only=args.metadata_only,
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
    if args.append and args.output.exists():
        urls = merge_url_lists(load_urls_from_file(args.output), urls)
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
    urls_output = args.urls_output or args.output_dir / _app_config(args).urls_output
    if args.append and urls_output.exists():
        scraped_urls = merge_url_lists(load_urls_from_file(urls_output), scraped_urls)
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
    if args.append and args.urls_output.exists():
        urls = merge_url_lists(load_urls_from_file(args.urls_output), urls)
    write_urls_to_file(urls, args.urls_output)
    LOGGER.info("Scraped URLs: %s", len(urls))
    LOGGER.info("File written: %s", args.urls_output)

    if not args.download:
        return 0

    report = download_urls(_download_config_from_args(args, urls, "browser-scrape", "scrape"))
    _write_download_reports(args, report)
    LOGGER.info("Status counts: %s", report.status_counts())
    return 1 if report.failed_count else 0


def run_retry_command(args: argparse.Namespace) -> int:
    original_report = read_report_file(args.report)
    urls = failed_urls_from_report(original_report)
    if not urls:
        LOGGER.info("No failed URLs to retry.")
        return 0

    if args.output_dir is None:
        metadata_output_dir = original_report.metadata.get("output_dir")
        args.output_dir = (
            Path(metadata_output_dir)
            if metadata_output_dir
            else _app_config(args).output_dir
        )

    report = download_urls(_download_config_from_args(args, urls, "retry", "report"))
    report.metadata["retry_report"] = str(args.report)
    _write_download_reports(args, report)
    LOGGER.info("Retried URLs: %s", len(urls))
    LOGGER.info("Status counts: %s", report.status_counts())
    return 1 if report.failed_count else 0


def run_summary_command(args: argparse.Namespace) -> int:
    report = read_report_file(args.report)
    summary = summarize_report(report, top=args.top)
    print(_format_summary(summary))
    return 0


def run_gallery_command(args: argparse.Namespace) -> int:
    report = read_report_file(args.report)
    output = args.output or args.report.parent / "index.html"
    write_html_gallery(report, output)
    LOGGER.info("Gallery written: %s", output)
    return 0


def run_diff_command(args: argparse.Namespace) -> int:
    diff = diff_url_files(args.old, args.new)
    print(_format_url_diff(diff))
    return 0


def _format_summary(summary: dict) -> str:
    lines = [
        f"Command: {summary['command']}",
        f"Started: {summary['started_at'] or 'unknown'}",
        f"Finished: {summary['finished_at'] or 'unknown'}",
        f"Total URLs: {summary['total_urls']}",
        f"Comments saved: {summary['comment_count']}",
        f"Status counts: {_format_counts(summary['status_counts'])}",
    ]
    if summary["error_type_counts"]:
        lines.append(f"Error types: {_format_counts(summary['error_type_counts'])}")
    if summary["top_tags"]:
        tags = ", ".join(f"#{tag} ({count})" for tag, count in summary["top_tags"])
        lines.append(f"Top tags: {tags}")
    if summary["failed_urls"]:
        lines.append("Failed URLs:")
        lines.extend(f"  {url}" for url in summary["failed_urls"])
    if summary["output_paths"]:
        lines.append("Output paths:")
        lines.extend(f"  {path}" for path in summary["output_paths"])
    return "\n".join(lines)


def _format_url_diff(diff: dict[str, list[str]]) -> str:
    lines: list[str] = []
    for label in ("added", "removed", "shared"):
        urls = diff[label]
        lines.append(f"{label.title()} ({len(urls)}):")
        lines.extend(f"  {url}" for url in urls)
    return "\n".join(lines)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))


def _extract_config_arg(argv: Sequence[str] | None) -> tuple[Path | None, list[str]]:
    args = list(sys.argv[1:] if argv is None else argv)
    cleaned_args: list[str] = []
    config_file: Path | None = None
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--config":
            if index + 1 >= len(args):
                raise ValueError("--config requires a path.")
            config_file = Path(args[index + 1])
            index += 2
            continue
        if arg.startswith("--config="):
            config_file = Path(arg.split("=", 1)[1])
            index += 1
            continue
        cleaned_args.append(arg)
        index += 1
    return config_file, cleaned_args


def build_argument_parser(app_config: AppConfig = CONFIG) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Back up visible Instagram reel/post/tv URLs from your own browser session."
    )
    parser.add_argument(
        "--config",
        default=None,
        type=Path,
        help="Read defaults from a TOML config file instead of the packaged config.",
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
        default=app_config.resolved_urls_output,
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
        default=app_config.urls_output,
        type=Path,
        help="Scraped URL output file.",
    )
    scrape_parser.add_argument(
        "--append",
        action="store_true",
        help="Merge scraped URLs into the existing output file instead of replacing it.",
    )
    _add_scrape_options(scrape_parser, app_config)
    scrape_parser.set_defaults(func=run_scrape_command)

    download_parser = subparsers.add_parser(
        "download",
        help="Download URLs from a text file with yt-dlp.",
    )
    download_parser.add_argument("--input", required=True, type=Path, help="Input URL file.")
    _add_download_options(download_parser, app_config)
    download_parser.set_defaults(func=run_download_command)

    backup_parser = subparsers.add_parser(
        "backup",
        help="Scrape visible URLs, save them, download them, and write reports.",
    )
    _add_scrape_options(backup_parser, app_config)
    _add_download_options(backup_parser, app_config)
    backup_parser.add_argument(
        "--urls-output",
        default=None,
        type=Path,
        help="Scraped URL file. Defaults to OUTPUT_DIR/scraped_instagram_urls.txt.",
    )
    backup_parser.add_argument(
        "--append",
        action="store_true",
        help="Merge scraped URLs into the existing URL file before downloading.",
    )
    backup_parser.set_defaults(func=run_backup_command)

    retry_parser = subparsers.add_parser(
        "retry",
        help="Retry failed URLs from a previous JSON report.",
    )
    retry_parser.add_argument("--report", required=True, type=Path, help="JSON report file.")
    _add_download_options(retry_parser, app_config, use_config_output_dir=False)
    retry_parser.set_defaults(func=run_retry_command)

    summary_parser = subparsers.add_parser(
        "summary",
        help="Print a readable summary of a JSON report.",
    )
    summary_parser.add_argument("--report", required=True, type=Path, help="JSON report file.")
    summary_parser.add_argument(
        "--top",
        default=10,
        type=positive_int,
        help="Number of top hashtags to show.",
    )
    summary_parser.set_defaults(func=run_summary_command)

    gallery_parser = subparsers.add_parser(
        "gallery",
        help="Write a local HTML gallery from a JSON report.",
    )
    gallery_parser.add_argument("--report", required=True, type=Path, help="JSON report file.")
    gallery_parser.add_argument(
        "--output",
        default=None,
        type=Path,
        help="HTML output file. Defaults to index.html next to the report.",
    )
    gallery_parser.set_defaults(func=run_gallery_command)

    diff_parser = subparsers.add_parser(
        "diff",
        help="Compare two URL files.",
    )
    diff_parser.add_argument("--old", required=True, type=Path, help="Earlier URL file.")
    diff_parser.add_argument("--new", required=True, type=Path, help="Newer URL file.")
    diff_parser.set_defaults(func=run_diff_command)

    workaround_parser = subparsers.add_parser(
        "workaround",
        help="Deprecated alias: normalize a URL file and optionally download it.",
    )
    workaround_parser.add_argument("--urls-file", required=True, type=Path, help="Input URL file.")
    workaround_parser.add_argument(
        "--resolved-urls-file",
        default=app_config.resolved_urls_output,
        type=Path,
        help="Normalized URL output file.",
    )
    _add_download_options(workaround_parser, app_config)
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
        default=app_config.urls_output,
        type=Path,
        help="Scraped URL output file.",
    )
    _add_scrape_options(browser_parser, app_config)
    _add_download_options(browser_parser, app_config)
    browser_parser.add_argument(
        "--append",
        action="store_true",
        help="Merge scraped URLs into the existing URL file instead of replacing it.",
    )
    browser_parser.add_argument(
        "--download",
        action="store_true",
        help="Download after scraping.",
    )
    browser_parser.set_defaults(func=run_browser_scrape_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    try:
        config_file, parse_argv = _extract_config_arg(argv)
        app_config = load_config(config_file)
    except (FileNotFoundError, OSError, KeyError, TypeError, ValueError) as exc:
        LOGGER.error("Could not load config: %s", exc)
        return 1

    parser = build_argument_parser(app_config)
    args = parser.parse_args(parse_argv)
    args.config = config_file
    args.app_config = app_config

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
