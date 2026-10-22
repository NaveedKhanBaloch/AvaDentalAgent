from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_health() -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready_health() -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_system_info() -> None:
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    assert response.json()["app"] == "DentalVoice AI"
