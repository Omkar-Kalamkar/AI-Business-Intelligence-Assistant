import pytest
from fastapi.testclient import TestClient

import main

PASSWORD = "StrongPass123!"


@pytest.fixture
def client():
    main.app.dependency_overrides.clear()
    return TestClient(main.app)


def register_admin(client):
    assert client.post(
        "/auth/register",
        json={
            "email": "owner-a@example.com",
            "full_name": "Owner A",
            "password": PASSWORD,
            "role": "admin",
        },
    ).status_code == 201
    return client.post(
        "/auth/login",
        json={"email": "owner-a@example.com", "password": PASSWORD},
    ).json()["access_token"]


def create_analyst(client, admin_token):
    response = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "owner-b@example.com",
            "full_name": "Owner B",
            "password": PASSWORD,
            "role": "analyst",
        },
    )
    assert response.status_code == 201
    return client.post(
        "/auth/login",
        json={"email": "owner-b@example.com", "password": PASSWORD},
    ).json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def upload_csv(client, token, product, sales):
    content = (
        "Date,Product,Region,Sales,Profit,Quantity\n"
        f"2024-01-01,{product},North,{sales},20,1\n"
        f"2024-01-02,{product},South,{sales + 100},40,2\n"
    ).encode("utf-8")
    response = client.post(
        "/upload",
        headers=auth(token),
        files={"file": ("sales.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    return response.json()


def test_datasets_reports_and_history_are_isolated_per_owner(client):
    admin_token = register_admin(client)
    analyst_token = create_analyst(client, admin_token)
    admin_headers = auth(admin_token)
    analyst_headers = auth(analyst_token)

    admin_upload = upload_csv(client, admin_token, "Mobile", 100)
    analyst_upload = upload_csv(client, analyst_token, "Laptop", 500)

    assert admin_upload["dataset_id"] != analyst_upload["dataset_id"]

    admin_insights = client.get(
        "/insights?save=false", headers=admin_headers
    ).json()
    analyst_insights = client.get(
        "/insights?save=false", headers=analyst_headers
    ).json()
    assert admin_insights["dataset_id"] == admin_upload["dataset_id"]
    assert analyst_insights["dataset_id"] == analyst_upload["dataset_id"]

    admin_history = client.get("/history", headers=admin_headers).json()
    analyst_history = client.get("/history", headers=analyst_headers).json()
    assert admin_history["total"] == 1
    assert analyst_history["total"] == 1

    admin_insight_id = client.get("/insights", headers=admin_headers).json()[
        "insight_id"
    ]
    analyst_report = client.post("/reports", headers=analyst_headers, json={})
    assert analyst_report.status_code == 201
    analyst_report_id = analyst_report.json()["id"]

    assert client.get(
        "/reports", headers=admin_headers
    ).json()["total"] == 0
    assert client.get(
        f"/reports/{analyst_report_id}", headers=admin_headers
    ).status_code == 404
    assert client.get(
        f"/reports/{analyst_report_id}/pdf", headers=admin_headers
    ).status_code == 404
    assert client.get(
        f"/reports/{analyst_report_id}/excel", headers=admin_headers
    ).status_code == 404
    assert client.delete(
        f"/reports/{analyst_report_id}", headers=admin_headers
    ).status_code == 404

    assert client.get(
        f"/history/{admin_insight_id}", headers=analyst_headers
    ).status_code == 404
    assert client.delete(
        f"/history/{admin_insight_id}", headers=analyst_headers
    ).status_code == 404
    assert client.get(
        f"/report/{admin_insight_id}", headers=analyst_headers
    ).status_code == 404

    admin_report = client.post("/reports", headers=admin_headers, json={})
    assert admin_report.status_code == 201
    admin_report_id = admin_report.json()["id"]

    assert client.get(
        "/reports", headers=analyst_headers
    ).json()["total"] == 1
    assert client.get(
        f"/reports/{admin_report_id}", headers=analyst_headers
    ).status_code == 404
    assert client.delete(
        f"/reports/{admin_report_id}", headers=analyst_headers
    ).status_code == 404


def test_viewer_sees_only_own_saved_data(client):
    admin_token = register_admin(client)

    client.post(
        "/admin/users",
        headers=auth(admin_token),
        json={
            "email": "viewer@example.com",
            "full_name": "Viewer",
            "password": PASSWORD,
            "role": "viewer",
        },
    )
    viewer_token = client.post(
        "/auth/login",
        json={"email": "viewer@example.com", "password": PASSWORD},
    ).json()["access_token"]

    upload_csv(client, admin_token, "Mobile", 100)

    viewer_history = client.get(
        "/history", headers=auth(viewer_token)
    ).json()
    assert viewer_history["total"] == 0
    assert client.get(
        "/reports", headers=auth(viewer_token)
    ).json()["total"] == 0
