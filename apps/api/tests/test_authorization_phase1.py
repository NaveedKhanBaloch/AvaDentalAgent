from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.core.security import hash_password, create_access_token
from app.db.session import SessionLocal
from app.models.models import Clinic, Tenant, Patient, User, Membership, Appointment

client = TestClient(app)


def test_strict_auth_missing_and_invalid(monkeypatch):
    monkeypatch.setattr(get_settings(), "strict_auth_mode", True)
    for route in ("/appointments", "/patients", "/operations/calls", "/dashboard/summary", "/providers", "/staff"):
        assert client.get("/api/v1" + route).status_code == 401
        assert client.get("/api/v1" + route, headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_two_clinic_requests_are_isolated(monkeypatch):
    monkeypatch.setattr(get_settings(), "strict_auth_mode", True)
    with SessionLocal() as db:
        owner = db.query(User).first()
        original = db.query(Patient).first()
        tenant = Tenant(name="Other", slug="other")
        db.add(tenant); db.flush()
        clinic = Clinic(tenant_id=tenant.id, name="Other", timezone="Asia/Karachi")
        user = User(email="other@example.com", full_name="Other", password_hash=hash_password("Synthetic123!"))
        db.add_all([clinic, user]); db.flush()
        db.add(Membership(user_id=user.id, tenant_id=tenant.id, clinic_id=clinic.id, role="receptionist"))
        db.add(Patient(tenant_id=tenant.id, clinic_id=clinic.id, first_name="Separate", last_name="Test"))
        db.commit()
    def patients(user_id):
        with TestClient(app) as separate:
            return separate.get("/api/v1/patients", headers={"Authorization": "Bearer " + create_access_token(user_id)}).json()["items"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, other = list(pool.map(patients, [owner.id, user.id]))
    assert original.id in {p["id"] for p in first}
    assert original.id not in {p["id"] for p in other}
    headers = {"Authorization": "Bearer " + create_access_token(user.id)}
    assert client.get(f"/api/v1/patients/{original.id}", headers=headers).status_code == 404
    with SessionLocal() as db:
        appointment = db.query(Appointment).first()
    assert client.get(f"/api/v1/appointments/{appointment.id}", headers=headers).status_code == 404
    assert client.delete(f"/api/v1/appointments/{appointment.id}", headers=headers).status_code == 404


def test_dentist_cannot_create_or_configure_schedule():
    with SessionLocal() as db:
        clinic = db.query(Clinic).first()
        user = User(email="dentist@example.com", full_name="Dentist", password_hash="unused")
        db.add(user); db.flush()
        db.add(Membership(user_id=user.id, tenant_id=clinic.tenant_id, clinic_id=clinic.id, role="dentist"))
        db.commit()
    headers = {"Authorization": "Bearer " + create_access_token(user.id)}
    assert client.post("/api/v1/appointments", headers=headers, json={"patient_id": "x", "start_time": "2026-11-10T10:00:00Z", "end_time": "2026-11-10T11:00:00Z"}).status_code == 403
    assert client.post("/api/v1/providers", headers=headers, json={"name": "Other"}).status_code == 403
