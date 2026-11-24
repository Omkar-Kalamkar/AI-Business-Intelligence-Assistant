import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_DB_PATH = Path(__file__).with_name("insights.db")


def _db_path():
    return Path(os.environ.get("INSIGHTS_DB_PATH", DEFAULT_DB_PATH))


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    _migrate(connection)
    return connection


def _migrate(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS insight_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            filename TEXT NOT NULL,
            dataset_hash TEXT,
            record_count INTEGER,
            payload TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_insight_history_created
        ON insight_history (created_at DESC)
        """
    )
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()


def _metadata(row):
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "kind": row["kind"],
        "filename": row["filename"],
        "dataset_hash": row["dataset_hash"],
        "record_count": row["record_count"],
    }


def save_insight(filename, payload, kind="business_insights",
                 dataset_hash=None, record_count=None):
    created_at = datetime.now(timezone.utc).isoformat()

    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO insight_history
                    (created_at, kind, filename, dataset_hash,
                     record_count, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    kind,
                    filename,
                    dataset_hash,
                    record_count,
                    json.dumps(payload, default=str),
                ),
            )
            insight_id = cursor.lastrowid

    return {
        "id": insight_id,
        "created_at": created_at,
        "kind": kind,
        "filename": filename,
        "dataset_hash": dataset_hash,
        "record_count": record_count,
    }


def list_insights(limit=50, offset=0):
    with closing(_connect()) as connection:
        with connection:
            rows = connection.execute(
                """
                SELECT id, created_at, kind, filename,
                       dataset_hash, record_count
                FROM insight_history
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

            total = connection.execute(
                "SELECT COUNT(*) AS total FROM insight_history"
            ).fetchone()["total"]

    return {
        "items": [_metadata(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_insight(insight_id):
    with closing(_connect()) as connection:
        with connection:
            row = connection.execute(
                "SELECT * FROM insight_history WHERE id = ?",
                (insight_id,),
            ).fetchone()

    if row is None:
        return None

    result = _metadata(row)
    result["payload"] = json.loads(row["payload"])
    return result


def delete_insight(insight_id):
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM insight_history WHERE id = ?",
                (insight_id,),
            )
    return cursor.rowcount > 0
