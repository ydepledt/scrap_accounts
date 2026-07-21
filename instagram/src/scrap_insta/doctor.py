from __future__ import annotations

import importlib.util
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .archive import resolve_archive_db
from .config import AppConfig
from .history import resolve_history_dir
from .models import DownloadConfig, ScrapeConfig


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


def run_doctor_checks(
    config: AppConfig,
    cookies_from_browser: str | None = None,
    cookies_file: Path | None = None,
) -> list[DoctorCheck]:
    checks = [
        _config_check(config),
        _writable_dir_check("output_dir", config.output_dir),
        _profile_dir_check(config.profile_dir),
        _writable_dir_check(
            "history_dir",
            resolve_history_dir(config.output_dir, config.history_dir),
        ),
        _writable_file_parent_check(
            "archive_db",
            resolve_archive_db(config.output_dir, config.archive_db),
        ),
        _module_check("playwright", "Playwright Python package"),
        _module_check("yt_dlp", "yt-dlp Python package"),
        _cookie_check(config, cookies_from_browser, cookies_file),
    ]
    return checks


def doctor_has_failures(checks: list[DoctorCheck]) -> bool:
    return any(check.status == "fail" for check in checks)


def format_doctor_checks(checks: list[DoctorCheck]) -> str:
    return "\n".join(
        f"{check.status.upper():4} {check.name}: {check.detail}"
        for check in checks
    )


def _config_check(config: AppConfig) -> DoctorCheck:
    try:
        ScrapeConfig(
            start_url=config.instagram_login_url,
            profile_dir=config.profile_dir,
            scrolls=config.scrolls,
            scroll_delay_ms=config.scroll_delay_ms,
            scroll_pixels=config.scroll_pixels,
            max_idle_scrolls=config.max_idle_scrolls,
            browser_width=config.browser_width,
            browser_height=config.browser_height,
        ).validate()
        DownloadConfig(urls=[], output_dir=config.output_dir).validate()
    except (FileNotFoundError, ValueError) as exc:
        return DoctorCheck("config", "fail", str(exc))
    return DoctorCheck("config", "pass", "config values are valid")


def _module_check(module_name: str, label: str) -> DoctorCheck:
    if importlib.util.find_spec(module_name) is None:
        return DoctorCheck(module_name, "fail", f"{label} is not importable")
    return DoctorCheck(module_name, "pass", f"{label} is importable")


def _profile_dir_check(profile_dir: Path) -> DoctorCheck:
    if profile_dir.exists():
        if profile_dir.is_dir():
            return DoctorCheck("profile_dir", "pass", f"exists: {profile_dir}")
        return DoctorCheck("profile_dir", "fail", f"not a directory: {profile_dir}")
    return DoctorCheck(
        "profile_dir",
        "warn",
        f"does not exist yet: {profile_dir}",
    )


def _writable_dir_check(name: str, directory: Path) -> DoctorCheck:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".doctor-", delete=True):
            pass
    except OSError as exc:
        return DoctorCheck(name, "fail", f"not writable: {exc}")
    return DoctorCheck(name, "pass", f"writable: {directory}")


def _writable_file_parent_check(name: str, file_path: Path) -> DoctorCheck:
    return _writable_dir_check(name, file_path.parent)


def _cookie_check(
    config: AppConfig,
    cookies_from_browser: str | None,
    cookies_file: Path | None,
) -> DoctorCheck:
    if cookies_from_browser and cookies_file:
        return DoctorCheck("cookies", "fail", "choose browser cookies or cookies file")
    if cookies_from_browser:
        if cookies_from_browser not in config.cookie_browser_choices:
            return DoctorCheck("cookies", "fail", f"unsupported browser: {cookies_from_browser}")
        return DoctorCheck("cookies", "pass", f"browser source accepted: {cookies_from_browser}")
    if cookies_file:
        if cookies_file.exists():
            return DoctorCheck("cookies", "pass", f"cookies file exists: {cookies_file}")
        return DoctorCheck("cookies", "fail", f"cookies file missing: {cookies_file}")
    return DoctorCheck("cookies", "warn", "no cookie source selected")
