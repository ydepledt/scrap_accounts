from __future__ import annotations

import importlib
import io
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

import app


@pytest.mark.parametrize("action", ["download", "download_selected"])
def test_existing_urls_reach_download_cli_without_new_scrape(tmp_path, monkeypatch, action):
    source_urls = [
        "https://www.instagram.com/reel/AAA/",
        "https://www.instagram.com/p/BBB/",
    ]
    source = tmp_path / ".local" / "share" / "scrap-accounts" / "Instagram" / "urls.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(source_urls) + "\n", encoding="utf-8")

    requested = [source_urls[1]] if action == "download_selected" else source_urls
    captured: dict[str, object] = {}

    def fake_main() -> int:
        args = sys.argv[1:]
        assert args[0] == "download"
        input_file = Path(args[args.index("--input") + 1])
        captured["urls"] = input_file.read_text(encoding="utf-8").splitlines()
        captured["output_dir"] = args[args.index("--output-dir") + 1]
        captured["comments_limit"] = args[args.index("--comments-limit") + 1]
        cookies = Path(args[args.index("--cookies-file") + 1])
        assert cookies.is_file()
        return 0

    module = SimpleNamespace(main=fake_main)
    original_import = importlib.import_module
    monkeypatch.setattr(
        importlib, "import_module",
        lambda name: module if name == "scrap_insta.cli" else original_import(name),
    )

    api = ModuleType("playwright.sync_api")
    class FakeContext:
        def cookies(self):
            return []
        def close(self):
            pass
    class FakePlaywright:
        chromium = SimpleNamespace(launch_persistent_context=lambda *a, **kw: FakeContext())
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            pass

    api.sync_playwright = lambda: FakePlaywright()
    monkeypatch.setitem(sys.modules, "playwright", ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", api)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(os, "getsid", lambda _pid: os.getpid())
    monkeypatch.setattr(sys, "stdin", io.StringIO("\n".join(requested)))
    monkeypatch.setattr(sys, "argv", ["-c", "Instagram", action, "100", "0", "25", "0"])

    with pytest.raises(SystemExit) as exc_info:
        exec(app.RUNNER, {"__name__": "__main__"})

    assert exc_info.value.code == 0
    assert captured["urls"] == requested
    assert captured["comments_limit"] == "25"
    assert source.read_text(encoding="utf-8").splitlines() == source_urls
