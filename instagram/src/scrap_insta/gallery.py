from __future__ import annotations

from html import escape
from pathlib import Path

from .models import RunReport

VIDEO_EXTENSIONS = {".m4v", ".mov", ".mp4", ".webm"}
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}


def write_html_gallery(report: RunReport, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(_gallery_html(report, output_file), encoding="utf-8")


def _gallery_html(report: RunReport, output_file: Path) -> str:
    items_html = "\n".join(_item_html(item, output_file.parent) for item in report.items)
    status_counts = ", ".join(
        f"{escape(status)}: {count}" for status, count in sorted(report.status_counts().items())
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Instagram Backup Gallery</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{
      margin: 0;
      background: Canvas;
      color: CanvasText;
    }}
    header, main {{
      margin: 0 auto;
      max-width: 1120px;
      padding: 24px;
    }}
    h1 {{
      font-size: 2rem;
      margin: 0 0 8px;
    }}
    .meta {{
      color: color-mix(in srgb, CanvasText 70%, transparent);
      margin: 0;
    }}
    .grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }}
    article {{
      border: 1px solid color-mix(in srgb, CanvasText 20%, transparent);
      border-radius: 8px;
      overflow: hidden;
    }}
    video, img {{
      aspect-ratio: 1 / 1;
      background: #111;
      display: block;
      object-fit: cover;
      width: 100%;
    }}
    .body {{
      padding: 12px;
    }}
    .status {{
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .tags {{
      color: color-mix(in srgb, CanvasText 68%, transparent);
      font-size: 0.9rem;
    }}
    a {{
      color: LinkText;
      overflow-wrap: anywhere;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Instagram Backup Gallery</h1>
    <p class="meta">
      {escape(report.command)} &middot; {escape(status_counts)} &middot; {report.total_urls} item(s)
    </p>
  </header>
  <main class="grid">
    {items_html}
  </main>
</body>
</html>
"""


def _item_html(item, base_dir: Path) -> str:
    media_html = _media_html(item.output_path, base_dir)
    description = escape(item.description or "")
    tags = " ".join(f"#{escape(tag)}" for tag in item.tags)
    comments = f"{len(item.comments)} comment(s)" if item.comments else "No comments saved"
    error = f"<p>{escape(item.error or '')}</p>" if item.error else ""
    return f"""<article>
  {media_html}
  <div class="body">
    <div class="status">{escape(item.status)}</div>
    <p><a href="{escape(item.url)}">{escape(item.url)}</a></p>
    <p>{description}</p>
    <p class="tags">{tags}</p>
    <p>{escape(comments)}</p>
    {error}
  </div>
</article>"""


def _media_html(output_path: str | None, base_dir: Path) -> str:
    if output_path is None:
        return ""

    path = Path(output_path)
    source = escape(_relative_media_path(path, base_dir))
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return f'<video src="{source}" controls preload="metadata"></video>'
    if suffix in IMAGE_EXTENSIONS:
        return f'<img src="{source}" alt="">'
    return f'<p><a href="{source}">{escape(path.name)}</a></p>'


def _relative_media_path(path: Path, base_dir: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(base_dir.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
