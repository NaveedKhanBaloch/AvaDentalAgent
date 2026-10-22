from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_success() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@harbordentaldemo.local", "password": "AdminPass123!"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_create_patient_success() -> None:
    response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Lucy",
            "last_name": "Smith",
            "phone": "555-0101",
            "email": "lucy.smith@example.com",
            "preferred_contact_method": "phone",
            "notes": "Demo patient",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["first_name"] == "Lucy"


def test_availability_success() -> None:
    response = client.post(
        "/api/v1/appointments/availability",
        json={"preferred_date": "2026-11-10", "time_preference": "morning"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert len(body["slots"]) > 0


def test_dashboard_summary() -> None:
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["appointments_today"] >= 0


def test_profile_loaded_from_jwt() -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@harbordentaldemo.local", "password": "AdminPass123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "admin@harbordentaldemo.local"
    assert body["role"] in {"Clinic Owner", "clinic_owner"}


def test_provider_and_service_catalogs() -> None:
    providers = client.get("/api/v1/providers")
    assert providers.status_code == 200, providers.text
    assert len(providers.json()["items"]) >= 1

    services = client.get("/api/v1/services")
    assert services.status_code == 200, services.text
    assert len(services.json()["items"]) >= 1


def test_weekend_availability_is_closed() -> None:
    response = client.post(
        "/api/v1/appointments/availability",
        json={"preferred_date": "2026-11-08", "time_preference": "morning"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "unavailable"
    assert len(body["slots"]) == 0
