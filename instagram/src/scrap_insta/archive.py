from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import DownloadItemResult, RunReport


def resolve_archive_db(output_dir: Path, archive_db: Path) -> Path:
    return archive_db if archive_db.is_absolute() else output_dir / archive_db


def index_report(report: RunReport, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    run_id = str(report.metadata.get("run_id") or _run_id_for(report))

    with sqlite3.connect(db_path) as connection:
        _init_schema(connection)
        connection.execute(
            """
            INSERT OR REPLACE INTO archive_runs
                (id, command, started_at, finished_at, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                report.command,
                report.started_at,
                report.finished_at,
                json.dumps(report.metadata, ensure_ascii=False, sort_keys=True),
            ),
        )
        for item in report.items:
            _upsert_item(connection, report, item)
            connection.execute(
                """
                INSERT INTO archive_history
                    (
                        run_id, url, status, output_path, media_id, duplicate_of,
                        error_type, error, recorded_at
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item.url,
                    item.status,
                    item.output_path,
                    item.media_id,
                    item.duplicate_of,
                    item.error_type,
                    item.error,
                    report.finished_at or report.started_at,
                ),
            )


def search_archive(
    db_path: Path,
    query: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    if not db_path.exists():
        raise FileNotFoundError(f"Archive database not found: {db_path}")

    where: list[str] = []
    values: list[object] = []
    if query:
        needle = f"%{query.lower()}%"
        where.append(
            """
            (
                lower(url) LIKE ?
                OR lower(coalesce(description, '')) LIKE ?
                OR lower(tags_json) LIKE ?
                OR lower(comments_json) LIKE ?
                OR lower(metadata_json) LIKE ?
            )
            """
        )
        values.extend([needle] * 5)
    if status:
        where.append("status = ?")
        values.append(status)
    if tag:
        where.append("lower(tags_json) LIKE ?")
        values.append(f"%{tag.lower()}%")

    sql = """
        SELECT
            url, status, output_path, media_id, duplicate_of, description,
            tags_json, comments_json, metadata_json, first_seen, last_seen, last_downloaded,
            error_type, error
        FROM archive_items
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY last_seen DESC, url ASC LIMIT ?"
    values.append(limit)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _init_schema(connection)
        rows = connection.execute(sql, values).fetchall()
    return [_row_to_dict(row) for row in rows]


def duplicate_groups(db_path: Path) -> list[dict[str, Any]]:
    if not db_path.exists():
        raise FileNotFoundError(f"Archive database not found: {db_path}")

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        _init_schema(connection)
        rows = connection.execute(
            """
            SELECT
                coalesce(media_id, output_path) AS duplicate_key,
                count(*) AS count,
                json_group_array(url) AS urls
            FROM archive_items
            WHERE coalesce(media_id, output_path) IS NOT NULL
            GROUP BY duplicate_key
            HAVING count(*) > 1
            ORDER BY count DESC, duplicate_key ASC
            """
        ).fetchall()
    return [
        {
            "duplicate_key": row["duplicate_key"],
            "count": row["count"],
            "urls": json.loads(row["urls"]),
        }
        for row in rows
    ]


def _init_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS archive_runs (
            id TEXT PRIMARY KEY,
            command TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            metadata_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS archive_items (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            output_path TEXT,
            media_id TEXT,
            duplicate_of TEXT,
            description TEXT,
            tags_json TEXT NOT NULL,
            comments_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            last_downloaded TEXT,
            error_type TEXT,
            error TEXT
        )
        """
    )
    # Migrate databases created before the rich metadata export.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(archive_items)")}
    if "metadata_json" not in columns:
        connection.execute("ALTER TABLE archive_items ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS archive_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            output_path TEXT,
            media_id TEXT,
            duplicate_of TEXT,
            error_type TEXT,
            error TEXT,
            recorded_at TEXT NOT NULL
        )
        """
    )


def _upsert_item(
    connection: sqlite3.Connection,
    report: RunReport,
    item: DownloadItemResult,
) -> None:
    observed_at = report.finished_at or report.started_at
    downloaded_at = observed_at if item.status == "downloaded" else None
    connection.execute(
        """
        INSERT INTO archive_items
            (
                url, status, output_path, media_id, duplicate_of, description,
                tags_json, comments_json, metadata_json, first_seen, last_seen, last_downloaded,
                error_type, error
            )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            status = excluded.status,
            output_path = coalesce(excluded.output_path, archive_items.output_path),
            media_id = coalesce(excluded.media_id, archive_items.media_id),
            duplicate_of = excluded.duplicate_of,
            description = coalesce(excluded.description, archive_items.description),
            tags_json = CASE WHEN excluded.status = 'failed' THEN archive_items.tags_json ELSE excluded.tags_json END,
            comments_json = CASE WHEN excluded.status = 'failed' THEN archive_items.comments_json ELSE excluded.comments_json END,
            metadata_json = CASE
                WHEN excluded.status = 'failed' OR excluded.metadata_json = '{}' THEN archive_items.metadata_json
                ELSE excluded.metadata_json
            END,
            last_seen = excluded.last_seen,
            last_downloaded = coalesce(excluded.last_downloaded, archive_items.last_downloaded),
            error_type = excluded.error_type,
            error = excluded.error
        """,
        (
            item.url,
            item.status,
            item.output_path,
            item.media_id,
            item.duplicate_of,
            item.description,
            json.dumps(item.tags, ensure_ascii=False),
            json.dumps(item.comments, ensure_ascii=False),
            json.dumps(item.metadata, ensure_ascii=False),
            observed_at,
            observed_at,
            downloaded_at,
            item.error_type,
            item.error,
        ),
    )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["tags"] = json.loads(result.pop("tags_json"))
    result["comments"] = json.loads(result.pop("comments_json"))
    result["metadata"] = json.loads(result.pop("metadata_json"))
    return result


def _run_id_for(report: RunReport) -> str:
    return f"{report.command}-{report.started_at}".replace(":", "").replace("+", "Z")
