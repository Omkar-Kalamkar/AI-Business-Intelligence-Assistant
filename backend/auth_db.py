import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import insight_history
from security import hash_password


ROLES = ("admin", "analyst", "viewer")
WRITE_ROLES = ("admin", "analyst")


class DuplicateEmail(Exception):
    pass


class UserNotFound(Exception):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _public_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def count_users():
    with closing(insight_history._connect()) as connection:
        with connection:
            return connection.execute(
                "SELECT COUNT(*) AS total FROM users"
            ).fetchone()["total"]


def get_user_by_email(email):
    with closing(insight_history._connect()) as connection:
        with connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
    return _public_user(row) if row else None


def get_user_by_id(user_id):
    with closing(insight_history._connect()) as connection:
        with connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    return _public_user(row) if row else None


def get_password_hash(user_id):
    with closing(insight_history._connect()) as connection:
        with connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    return row["password_hash"] if row else None


def get_token_version(user_id):
    with closing(insight_history._connect()) as connection:
        with connection:
            row = connection.execute(
                "SELECT token_version FROM users WHERE id = ?", (user_id,)
            ).fetchone()
    return int(row["token_version"]) if row else None


def list_users(limit=100, offset=0):
    with closing(insight_history._connect()) as connection:
        with connection:
            rows = connection.execute(
                """
                SELECT * FROM users ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            total = connection.execute(
                "SELECT COUNT(*) AS total FROM users"
            ).fetchone()["total"]
    return {
        "items": [_public_user(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def create_user(email, full_name, password, role="viewer", is_active=True):
    if role not in ROLES:
        raise ValueError("Unsupported role.")

    normalized_email = email.strip().lower()
    now = _now()
    try:
        with closing(insight_history._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users
                        (email, full_name, password_hash, role, is_active,
                         token_version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        normalized_email,
                        full_name.strip(),
                        hash_password(password),
                        role,
                        1 if is_active else 0,
                        now,
                        now,
                    ),
                )
                user_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise DuplicateEmail("An account with this email already exists.") from error

    return get_user_by_id(user_id)


def update_user(user_id, full_name=None, email=None, password=None):
    updates = []
    parameters = []

    if full_name is not None:
        updates.append("full_name = ?")
        parameters.append(full_name.strip())
    if email is not None:
        updates.append("email = ?")
        parameters.append(email.strip().lower())
    if password is not None:
        updates.append("password_hash = ?")
        updates.append("token_version = token_version + 1")
        parameters.append(hash_password(password))

    if not updates:
        return get_user_by_id(user_id)

    updates.append("updated_at = ?")
    parameters.extend([_now(), user_id])

    try:
        with closing(insight_history._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                    parameters,
                )
    except sqlite3.IntegrityError as error:
        raise DuplicateEmail("An account with this email already exists.") from error

    if cursor.rowcount == 0:
        raise UserNotFound("User not found.")
    return get_user_by_id(user_id)


def set_role(user_id, role):
    if role not in ROLES:
        raise ValueError("Unsupported role.")

    with closing(insight_history._connect()) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE users SET role = ?, updated_at = ? WHERE id = ?",
                (role, _now(), user_id),
            )
    if cursor.rowcount == 0:
        raise UserNotFound("User not found.")
    return get_user_by_id(user_id)


def set_active(user_id, is_active):
    with closing(insight_history._connect()) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (1 if is_active else 0, _now(), user_id),
            )
    if cursor.rowcount == 0:
        raise UserNotFound("User not found.")
    return get_user_by_id(user_id)


def increment_token_version(user_id):
    with closing(insight_history._connect()) as connection:
        with connection:
            connection.execute(
                """
                UPDATE users
                SET token_version = token_version + 1, updated_at = ?
                WHERE id = ?
                """,
                (_now(), user_id),
            )
