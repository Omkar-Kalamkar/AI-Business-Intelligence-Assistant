import os
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

import main
from security import TOKEN_TYPE, get_secret_key

PASSWORD = "StrongPass123!"


@pytest.fixture
def client():
    main.app.dependency_overrides.clear()
    return TestClient(main.app)


def register(client, email, role="viewer", password=PASSWORD):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "full_name": "Auth Test User",
            "password": password,
            "role": role,
        },
    )


def login(client, email, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def bootstrap_admin(client, email="admin@example.com"):
    response = register(client, email, role="admin")
    assert response.status_code == 201
    return login(client, email).json()["access_token"]


def test_first_account_must_be_admin(client):
    response = register(client, "first@example.com", role="viewer")
    assert response.status_code == 403
    assert "Admin" in response.json()["detail"]


def test_registration_login_and_authenticated_me(client):
    admin_token = bootstrap_admin(client)

    response = client.get("/auth/me", headers=headers(admin_token))
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"
    assert "password" not in str(body).lower()


def test_duplicate_registration_and_public_admin_registration(client):
    bootstrap_admin(client)

    duplicate = register(client, "admin@example.com", role="viewer")
    assert duplicate.status_code == 409

    elevated = register(client, "second@example.com", role="admin")
    assert elevated.status_code == 403


def test_invalid_credentials_are_rejected(client):
    bootstrap_admin(client)

    wrong_password = login(client, "admin@example.com", "WrongPass123!")
    assert wrong_password.status_code == 401

    unknown_user = login(client, "missing@example.com")
    assert unknown_user.status_code == 401


def test_protected_api_requires_token(client):
    assert client.get("/history").status_code == 401
    assert client.get("/reports").status_code == 401
    assert client.get("/health").status_code == 200


def test_expired_token_is_rejected(client):
    token = bootstrap_admin(client)
    user = client.get("/auth/me", headers=headers(token)).json()

    expired = jwt.encode(
        {
            "sub": str(user["id"]),
            "role": user["role"],
            "ver": 0,
            "type": TOKEN_TYPE,
            "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        get_secret_key(),
        algorithm="HS256",
    )

    response = client.get("/auth/me", headers=headers(expired))
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_viewer_permissions_and_admin_role_management(client):
    admin_token = bootstrap_admin(client)
    admin_headers = headers(admin_token)

    analyst = client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": "analyst@example.com",
            "full_name": "Analyst User",
            "password": PASSWORD,
            "role": "analyst",
        },
    )
    viewer = client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": "viewer@example.com",
            "full_name": "Viewer User",
            "password": PASSWORD,
            "role": "viewer",
        },
    )
    assert analyst.status_code == 201
    assert viewer.status_code == 201

    viewer_token = login(client, "viewer@example.com").json()["access_token"]
    viewer_headers = headers(viewer_token)
    analyst_token = login(client, "analyst@example.com").json()["access_token"]

    assert client.get("/admin/users", headers=viewer_headers).status_code == 403
    assert client.get("/admin/users", headers=admin_headers).status_code == 200

    csv_file = {
        "file": (
            "sales.csv",
            b"Date,Product,Region,Sales,Profit,Quantity\n"
            b"2024-01-01,Mobile,North,100,20,1\n"
            b"2024-01-02,Laptop,South,200,40,2\n",
            "text/csv",
        )
    }
    assert client.post("/upload", headers=viewer_headers, files=csv_file).status_code == 403
    assert client.post("/reports", headers=viewer_headers, json={}).status_code == 403
    assert client.get("/insights", headers=viewer_headers).status_code == 403
    assert client.get("/insights?save=false", headers=viewer_headers).status_code == 400

    assert client.post(
        "/upload", headers=headers(analyst_token), files=csv_file
    ).status_code == 200
    assert client.post(
        "/reports", headers=headers(analyst_token), json={}
    ).status_code == 201

    promoted = client.patch(
        f"/admin/users/{viewer.json()['user']['id']}",
        headers=admin_headers,
        json={"role": "analyst"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["user"]["role"] == "analyst"


def test_logout_invalidates_existing_token(client):
    token = bootstrap_admin(client)

    assert client.get("/auth/me", headers=headers(token)).status_code == 200
    assert client.post("/auth/logout", headers=headers(token)).status_code == 200
    assert client.get("/auth/me", headers=headers(token)).status_code == 401


def test_viewer_exports_do_not_create_saved_insights(client):
    admin_token = bootstrap_admin(client)
    admin_headers = headers(admin_token)

    created = client.post(
        "/admin/users",
        headers=admin_headers,
        json={
            "email": "temporary@example.com",
            "full_name": "Temporary Analyst",
            "password": PASSWORD,
            "role": "analyst",
        },
    )
    user_id = created.json()["user"]["id"]
    analyst_token = login(client, "temporary@example.com").json()["access_token"]

    upload = client.post(
        "/upload",
        headers=headers(analyst_token),
        files={
            "file": (
                "sales.csv",
                b"Date,Product,Region,Sales,Profit,Quantity\n"
                b"2024-01-01,Mobile,North,100,20,1\n"
                b"2024-01-02,Laptop,South,200,40,2\n",
                "text/csv",
            )
        },
    )
    assert upload.status_code == 200

    client.patch(
        f"/admin/users/{user_id}",
        headers=admin_headers,
        json={"role": "viewer"},
    )

    response = client.get(
        "/reports/current/pdf", headers=headers(analyst_token)
    )
    assert response.status_code == 200

    kinds = [
        item["kind"]
        for item in client.get(
            "/history", headers=headers(analyst_token)
        ).json()["items"]
    ]
    assert kinds == ["upload_analysis"]


def test_password_change_and_profile_update(client):
    token = bootstrap_admin(client)
    auth_headers = headers(token)

    profile = client.patch(
        "/auth/profile",
        headers=auth_headers,
        json={"full_name": "Renamed Admin", "email": "admin2@example.com"},
    )
    assert profile.status_code == 200
    assert profile.json()["user"]["full_name"] == "Renamed Admin"

    change = client.post(
        "/auth/change-password",
        headers=auth_headers,
        json={"current_password": PASSWORD, "new_password": "NewStrongPass123!"},
    )
    assert change.status_code == 200
    assert client.get("/auth/me", headers=auth_headers).status_code == 401
    assert login(client, "admin2@example.com", "NewStrongPass123!").status_code == 200


def test_legacy_records_are_preserved_and_claimed_by_first_admin(client):
    db_path = os.environ["INSIGHTS_DB_PATH"]
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE insight_history (
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
        INSERT INTO insight_history
            (created_at, kind, filename, dataset_hash, record_count, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "2026-01-01T00:00:00+00:00",
            "business_report",
            "legacy.csv",
            "legacy-hash",
            10,
            '{"report_version": 1, "title": "Legacy"}',
        ),
    )
    connection.execute("PRAGMA user_version = 1")
    connection.commit()
    connection.close()

    token = bootstrap_admin(client)
    auth_headers = headers(token)

    listing = client.get("/history", headers=auth_headers).json()
    assert listing["total"] == 1
    assert listing["items"][0]["filename"] == "legacy.csv"

    detail = client.get("/history/1", headers=auth_headers).json()
    assert detail["payload"]["title"] == "Legacy"

    connection = sqlite3.connect(db_path)
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    owner_id = connection.execute(
        "SELECT owner_id FROM insight_history WHERE id = 1"
    ).fetchone()[0]
    connection.close()
    assert version == 2
    assert owner_id == 1
