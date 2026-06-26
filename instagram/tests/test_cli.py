from __future__ import annotations

import json

import pytest

from scrap_insta import cli


def test_cli_help_exits_successfully(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    assert exc_info.value.code == 0
    assert "normalize" in capsys.readouterr().out


def test_cli_rejects_invalid_scroll_argument() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["scrape", "--scrolls", "-1"])

    assert exc_info.value.code == 2


def test_cli_rejects_negative_comments_limit() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["download", "--input", "urls.txt", "--comments-limit", "-1"])

    assert exc_info.value.code == 2


def test_cli_rejects_unlimited_scrolls_without_stop_condition() -> None:
    assert cli.main(["scrape", "--unlimited-scrolls", "--headless"]) == 1


def test_cli_normalize_command(tmp_path) -> None:
    input_file = tmp_path / "raw.txt"
    output_file = tmp_path / "urls.txt"
    input_file.write_text("https://instagram.com/reel/BBB?utm=1\n", encoding="utf-8")

    assert cli.main(["normalize", "--input", str(input_file), "--output", str(output_file)]) == 0
    assert output_file.read_text(encoding="utf-8") == "https://www.instagram.com/reel/BBB/\n"


def test_cli_scrape_append_merges_existing_file(tmp_path, monkeypatch) -> None:
    output_file = tmp_path / "urls.txt"
    output_file.write_text("https://instagram.com/p/AAA\n", encoding="utf-8")
    seen_dimensions = []

    def fake_scrape(config):
        seen_dimensions.append((config.browser_width, config.browser_height))
        return ["https://www.instagram.com/reel/BBB/"]

    monkeypatch.setattr(cli, "scrape_visible_urls", fake_scrape)

    assert (
        cli.main(
            [
                "scrape",
                "--output",
                str(output_file),
                "--append",
                "--browser-width",
                "777",
                "--browser-height",
                "555",
            ]
        )
        == 0
    )
    assert output_file.read_text(encoding="utf-8") == (
        "https://www.instagram.com/p/AAA/\n"
        "https://www.instagram.com/reel/BBB/\n"
    )
    assert seen_dimensions == [(777, 555)]


def test_cli_download_dry_run_writes_reports(tmp_path) -> None:
    input_file = tmp_path / "urls.txt"
    output_dir = tmp_path / "downloads"
    input_file.write_text("https://instagram.com/p/AAA?x=1\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "download",
                "--input",
                str(input_file),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ]
        )
        == 0
    )

    report = json.loads((output_dir / "download_report.json").read_text(encoding="utf-8"))
    assert report["status_counts"] == {"dry_run": 1}


def test_cli_retry_uses_failed_urls_from_report(tmp_path) -> None:
    output_dir = tmp_path / "downloads"
    report_file = tmp_path / "download_report.json"
    report_file.write_text(
        json.dumps(
            {
                "command": "download",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "metadata": {"output_dir": str(output_dir)},
                "items": [
                    {
                        "url": "https://www.instagram.com/reel/AAA/",
                        "source": "input",
                        "status": "failed",
                        "error": "login required",
                    },
                    {
                        "url": "https://www.instagram.com/reel/BBB/",
                        "source": "input",
                        "status": "downloaded",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert cli.main(["retry", "--report", str(report_file), "--dry-run"]) == 0

    retry_report = json.loads((output_dir / "retry_report.json").read_text(encoding="utf-8"))
    assert retry_report["status_counts"] == {"dry_run": 1}
    assert retry_report["items"][0]["url"] == "https://www.instagram.com/reel/AAA/"


def test_cli_summary_gallery_and_diff_commands(tmp_path, capsys) -> None:
    media_file = tmp_path / "clip.mp4"
    media_file.write_text("placeholder", encoding="utf-8")
    report_file = tmp_path / "download_report.json"
    report_file.write_text(
        json.dumps(
            {
                "command": "download",
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "metadata": {},
                "items": [
                    {
                        "url": "https://www.instagram.com/reel/AAA/",
                        "source": "input",
                        "status": "downloaded",
                        "output_path": str(media_file),
                        "tags": ["tag"],
                        "comments": [{"text": "nice"}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    old_file = tmp_path / "old.txt"
    new_file = tmp_path / "new.txt"
    old_file.write_text("https://instagram.com/p/OLD\n", encoding="utf-8")
    new_file.write_text("https://instagram.com/p/NEW\n", encoding="utf-8")

    assert cli.main(["summary", "--report", str(report_file)]) == 0
    assert "Top tags: #tag (1)" in capsys.readouterr().out

    gallery_file = tmp_path / "gallery.html"
    assert cli.main(["gallery", "--report", str(report_file), "--output", str(gallery_file)]) == 0
    assert "Instagram Backup Gallery" in gallery_file.read_text(encoding="utf-8")

    assert cli.main(["diff", "--old", str(old_file), "--new", str(new_file)]) == 0
    diff_output = capsys.readouterr().out
    assert "Added (1):" in diff_output
    assert "https://www.instagram.com/p/NEW/" in diff_output


def test_cli_config_override_can_appear_after_subcommand(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    raw_file = tmp_path / "raw.txt"
    resolved_file = tmp_path / "custom_resolved.txt"
    raw_file.write_text("https://instagram.com/reel/AAA\n", encoding="utf-8")
    config_file.write_text(
        f"""
[paths]
output_dir = "{tmp_path / 'downloads'}"
profile_dir = "{tmp_path / 'profile'}"
urls_output = "{tmp_path / 'urls.txt'}"
resolved_urls_output = "{resolved_file}"

[scrape]
start_url = "https://www.instagram.com/accounts/login/"
scrolls = 1
scroll_delay_ms = 1
scroll_pixels = 100
browser_width = 800
browser_height = 600
max_idle_scrolls = 1

[download]
retries = 0
comments_limit = 0
cookie_browser_choices = ["chrome"]
""",
        encoding="utf-8",
    )

    assert cli.main(["normalize", "--config", str(config_file), "--input", str(raw_file)]) == 0
    assert resolved_file.read_text(encoding="utf-8") == "https://www.instagram.com/reel/AAA/\n"


def test_cli_workaround_alias_normalizes_without_download(tmp_path) -> None:
    input_file = tmp_path / "raw.txt"
    output_file = tmp_path / "resolved.txt"
    input_file.write_text("https://instagram.com/tv/CCC\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "workaround",
                "--urls-file",
                str(input_file),
                "--resolved-urls-file",
                str(output_file),
            ]
        )
        == 0
    )
    assert output_file.read_text(encoding="utf-8") == "https://www.instagram.com/tv/CCC/\n"
