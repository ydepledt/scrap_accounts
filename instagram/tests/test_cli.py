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
