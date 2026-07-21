from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from .browser import scrape_visible_urls
from .config import CONFIG, AppConfig, load_config
from .downloader import download_urls
from .files import load_urls_from_file, merge_url_lists, write_urls_to_file
from .models import DownloadConfig, DownloadItemResult, RunReport, ScrapeConfig
from .reports import summarize_report, write_report_files

LOGGER = logging.getLogger(__name__)

SOURCE_PAGE_URLS = {
    "manual": None,
    "home": "https://www.youtube.com/",
    "history": "https://www.youtube.com/feed/history",
    "liked-videos": "https://www.youtube.com/playlist?list=LL",
    "playlists": "https://www.youtube.com/feed/playlists",
    "subscriptions": "https://www.youtube.com/feed/subscriptions",
}


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


def _add_scrape_options(parser: argparse.ArgumentParser, config: AppConfig) -> None:
    parser.add_argument(
        "--source-page",
        choices=sorted(SOURCE_PAGE_URLS),
        default="manual",
        help="YouTube account page to open before scraping.",
    )
    parser.add_argument(
        "--start-url",
        default=config.youtube_start_url,
        help="Page opened when --source-page manual is used.",
    )
    parser.add_argument("--profile-dir", default=config.profile_dir, type=Path)
    parser.add_argument("--scrolls", default=config.scrolls, type=non_negative_int)
    parser.add_argument("--unlimited-scrolls", action="store_true")
    parser.add_argument("--scroll-delay-ms", default=config.scroll_delay_ms, type=non_negative_int)
    parser.add_argument("--scroll-pixels", default=config.scroll_pixels, type=positive_int)
    parser.add_argument("--browser-width", default=config.browser_width, type=positive_int)
    parser.add_argument("--browser-height", default=config.browser_height, type=positive_int)
    parser.add_argument("--limit", default=None, type=positive_int)
    parser.add_argument("--max-idle-scrolls", default=config.max_idle_scrolls, type=positive_int)
    parser.add_argument("--stop-when-no-new", action="store_true")
    parser.add_argument("--headless", action="store_true")


def _add_download_options(parser: argparse.ArgumentParser, config: AppConfig) -> None:
    parser.add_argument("--output-dir", default=config.output_dir, type=Path)
    _add_cookie_options(parser, config)
    parser.add_argument("--archive-file", default=None, type=Path)
    parser.add_argument("--retries", default=config.retries, type=non_negative_int)
    parser.add_argument("--comments-limit", default=config.comments_limit, type=non_negative_int)
    parser.add_argument("--format", dest="format_selector", default=config.format_selector)
    parser.add_argument(
        "--audio-only",
        action=argparse.BooleanOptionalAction,
        default=config.audio_only,
    )
    parser.add_argument(
        "--write-thumbnail",
        action=argparse.BooleanOptionalAction,
        default=config.write_thumbnail,
    )
    parser.add_argument(
        "--metadata-only",
        action=argparse.BooleanOptionalAction,
        default=config.metadata_only,
    )
    parser.add_argument(
        "--include-playlists",
        action=argparse.BooleanOptionalAction,
        default=config.include_playlists,
        help="Allow yt-dlp to expand playlist URLs.",
    )
    parser.add_argument("--overwrite", dest="skip_existing", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-dir", default=None, type=Path)
    parser.set_defaults(skip_existing=True)


def _scrape_config_from_args(args: argparse.Namespace) -> ScrapeConfig:
    source_url = SOURCE_PAGE_URLS[args.source_page]
    return ScrapeConfig(
        start_url=source_url or args.start_url,
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
        cookie_browser_choices=_app_config(args).cookie_browser_choices,
        archive_file=args.archive_file,
        retries=args.retries,
        comments_limit=args.comments_limit,
        format_selector=args.format_selector,
        audio_only=args.audio_only,
        write_thumbnail=args.write_thumbnail,
        metadata_only=args.metadata_only,
        include_playlists=args.include_playlists,
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


def _format_summary(summary: dict) -> str:
    lines = [
        f"Command: {summary['command']}",
        f"Started: {summary['started_at'] or 'unknown'}",
        f"Finished: {summary['finished_at'] or 'unknown'}",
        f"Total URLs: {summary['total_urls']}",
        f"Comments saved: {summary['comment_count']}",
        f"Views: {summary['view_count']}",
        f"Likes: {summary['like_count']}",
        f"Status counts: {_format_counts(summary['status_counts'])}",
    ]
    if summary["top_tags"]:
        tags = ", ".join(f"#{tag} ({count})" for tag, count in summary["top_tags"])
        lines.append(f"Top tags: {tags}")
    if summary["failed_urls"]:
        lines.append("Failed URLs:")
        lines.extend(f"  {url}" for url in summary["failed_urls"])
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
        description="Back up visible YouTube URLs from your own browser session."
    )
    parser.add_argument("--config", default=None, type=Path)
    parser.add_argument("--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize_parser = subparsers.add_parser("normalize")
    normalize_parser.add_argument("--input", required=True, type=Path)
    normalize_parser.add_argument("--output", default=app_config.resolved_urls_output, type=Path)
    normalize_parser.set_defaults(func=run_normalize_command)

    scrape_parser = subparsers.add_parser("scrape")
    scrape_parser.add_argument("--output", default=app_config.urls_output, type=Path)
    scrape_parser.add_argument("--append", action="store_true")
    _add_scrape_options(scrape_parser, app_config)
    scrape_parser.set_defaults(func=run_scrape_command)

    download_parser = subparsers.add_parser("download")
    download_parser.add_argument("--input", required=True, type=Path)
    _add_download_options(download_parser, app_config)
    download_parser.set_defaults(func=run_download_command)

    backup_parser = subparsers.add_parser("backup")
    _add_scrape_options(backup_parser, app_config)
    _add_download_options(backup_parser, app_config)
    backup_parser.add_argument("--urls-output", default=None, type=Path)
    backup_parser.add_argument("--append", action="store_true")
    backup_parser.set_defaults(func=run_backup_command)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--report", required=True, type=Path)
    summary_parser.add_argument("--top", default=10, type=positive_int)

    def run_summary_command(args: argparse.Namespace) -> int:
        import json

        payload = json.loads(args.report.read_text(encoding="utf-8"))
        items = [
            DownloadItemResult(
                url=str(item.get("url", "")),
                source=str(item.get("source", "")),
                status=str(item.get("status", "")),
                output_path=item.get("output_path") if isinstance(item.get("output_path"), str) else None,
                media_id=item.get("media_id") if isinstance(item.get("media_id"), str) else None,
                duplicate_of=item.get("duplicate_of") if isinstance(item.get("duplicate_of"), str) else None,
                description=item.get("description") if isinstance(item.get("description"), str) else None,
                tags=item.get("tags") if isinstance(item.get("tags"), list) else [],
                comments=item.get("comments") if isinstance(item.get("comments"), list) else [],
                stats=item.get("stats") if isinstance(item.get("stats"), dict) else {},
                error_type=item.get("error_type") if isinstance(item.get("error_type"), str) else None,
                error=item.get("error") if isinstance(item.get("error"), str) else None,
            )
            for item in payload.get("items", [])
            if isinstance(item, dict)
        ]
        report = RunReport(
            command=str(payload.get("command", "unknown")),
            started_at=str(payload.get("started_at", "")),
            finished_at=payload.get("finished_at") if isinstance(payload.get("finished_at"), str) else None,
            items=items,
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )
        print(_format_summary(summarize_report(report, top=args.top)))
        return 0

    summary_parser.set_defaults(func=run_summary_command)

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
