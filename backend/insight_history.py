import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 2
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
            payload TEXT NOT NULL,
            owner_id INTEGER
        )
        """
    )

    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(insight_history)"
        ).fetchall()
    }
    if "owner_id" not in columns:
        connection.execute(
            "ALTER TABLE insight_history ADD COLUMN owner_id INTEGER"
        )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            is_active INTEGER NOT NULL DEFAULT 1,
            token_version INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_insight_history_created
        ON insight_history (created_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_insight_history_owner
        ON insight_history (owner_id, id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_users_email
        ON users (email)
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
                 dataset_hash=None, record_count=None, owner_id=None):
    created_at = datetime.now(timezone.utc).isoformat()

    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO insight_history
                    (created_at, kind, filename, dataset_hash,
                     record_count, payload, owner_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    kind,
                    filename,
                    dataset_hash,
                    record_count,
                    json.dumps(payload, default=str),
                    owner_id,
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
        "owner_id": owner_id,
    }


def _where_clause(kind, owner_id):
    conditions = []
    parameters = []

    if kind is not None:
        conditions.append("kind = ?")
        parameters.append(kind)
    if owner_id is not None:
        conditions.append("owner_id = ?")
        parameters.append(owner_id)

    if not conditions:
        return "", parameters
    return " WHERE " + " AND ".join(conditions), parameters


def list_insights(limit=50, offset=0, kind=None, owner_id=None):
    where, parameters = _where_clause(kind, owner_id)

    with closing(_connect()) as connection:
        with connection:
            rows = connection.execute(
                f"""
                SELECT id, created_at, kind, filename,
                       dataset_hash, record_count
                FROM insight_history
                {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (*parameters, limit, offset),
            ).fetchall()

            total = connection.execute(
                f"SELECT COUNT(*) AS total FROM insight_history{where}",
                parameters,
            ).fetchone()["total"]

    return {
        "items": [_metadata(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_insight(insight_id, owner_id=None):
    owner_clause, parameters = (" AND owner_id = ?", [owner_id]) \
        if owner_id is not None else ("", [])

    with closing(_connect()) as connection:
        with connection:
            row = connection.execute(
                f"SELECT * FROM insight_history WHERE id = ?{owner_clause}",
                (insight_id, *parameters),
            ).fetchone()

    if row is None:
        return None

    result = _metadata(row)
    result["owner_id"] = row["owner_id"]
    result["payload"] = json.loads(row["payload"])
    return result


def delete_insight(insight_id, owner_id=None):
    owner_clause, parameters = (" AND owner_id = ?", [owner_id]) \
        if owner_id is not None else ("", [])

    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                f"DELETE FROM insight_history WHERE id = ?{owner_clause}",
                (insight_id, *parameters),
            )
    return cursor.rowcount > 0


def claim_orphan_insights(owner_id):
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE insight_history SET owner_id = ? WHERE owner_id IS NULL",
                (owner_id,),
            )
    return cursor.rowcount
