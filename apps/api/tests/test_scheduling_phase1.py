from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import (Appointment, Clinic, Provider, Patient, DentalService, ScheduleException,
                               ProviderWorkingHours, ProviderService, AuditLog, ClinicBusinessHours)
from app.services.scheduling import normalize_datetime, ScheduleValidationError

client = TestClient(app)

def booking(**overrides):
    with SessionLocal() as db:
        p = db.query(Patient).first()
        provider = db.query(Provider).first()
        service = db.query(DentalService).filter(DentalService.default_duration_minutes == 30).first()
        return dict({"patient_id": p.id, "provider_id": provider.id, "service_id": service.id,
            "start_time": "2026-11-10T10:00:00-05:00", "end_time": "2026-11-10T10:30:00-05:00"}, **overrides)

@pytest.mark.parametrize("changes", [
    {"start_time": "2026-11-08T10:00:00-05:00", "end_time": "2026-11-08T10:30:00-05:00"},
    {"start_time": "2026-11-10T06:00:00-05:00", "end_time": "2026-11-10T06:30:00-05:00"},
    {"end_time": "2026-11-10T10:10:00-05:00"}, {"provider_id": "missing"}, {"service_id": "missing"},
    {"status": "invented"}, {"status": "completed"}])
def test_invalid_booking(changes):
    assert client.post("/api/v1/appointments", json=booking(**changes)).status_code == 400


def test_exception_and_provider_schedule():
    body = booking()
    with SessionLocal() as db:
        clinic = db.query(Clinic).first()
        db.add(ProviderWorkingHours(provider_id=body["provider_id"], weekday=1, opening_time="12:00", closing_time="16:00"))
        db.commit()
    assert client.post("/api/v1/appointments", json=body).status_code == 400
    body.update(start_time="2026-11-10T12:00:00-05:00", end_time="2026-11-10T12:30:00-05:00")
    with SessionLocal() as db:
        db.add(ScheduleException(clinic_id=clinic.id, provider_id=None, start_time=datetime(2026,11,10,17,tzinfo=timezone.utc),
                                 end_time=datetime(2026,11,10,18,tzinfo=timezone.utc)))
        db.commit()
    assert client.post("/api/v1/appointments", json=body).status_code == 400


def test_provider_compatibility_and_inactive():
    body = booking()
    with SessionLocal() as db:
        other = db.query(DentalService).filter(DentalService.id != body["service_id"]).first()
        db.add(ProviderService(provider_id=body["provider_id"], service_id=other.id))
        db.commit()
    assert client.post("/api/v1/appointments", json=body).status_code == 400
    with SessionLocal() as db:
        db.get(Provider, body["provider_id"]).active_status = False
        db.commit()
    assert client.post("/api/v1/appointments", json=body).status_code == 400


def test_reschedule_conflict_cancel_release_history():
    body = booking()
    first = client.post("/api/v1/appointments", json=body).json()["appointment_id"]
    second = client.post("/api/v1/appointments", json=booking(start_time="2026-11-10T11:00:00-05:00", end_time="2026-11-10T11:30:00-05:00")).json()["appointment_id"]
    moved = client.patch(f"/api/v1/appointments/{second}", json={"start_time": body["start_time"], "end_time": body["end_time"]})
    assert moved.status_code == 409
    assert client.delete(f"/api/v1/appointments/{first}").status_code == 200
    assert client.patch(f"/api/v1/appointments/{second}", json={"start_time": body["start_time"], "end_time": body["end_time"]}).status_code == 200
    assert client.patch(f"/api/v1/appointments/{first}/status", json={"status": "completed"}).status_code == 400
    history = client.get(f"/api/v1/appointments/{first}/history").json()["items"]
    assert len(history) == 2
    assert history[-1]["changes"]["before"]["status"] == "scheduled"

@pytest.mark.parametrize("value", ["2026-03-08T02:30:00", "2026-11-01T01:30:00"])
def test_invalid_dst_local_time(value):
    with pytest.raises(ScheduleValidationError):
        normalize_datetime(value, ZoneInfo("America/New_York"))

@pytest.mark.parametrize("value", ["2026-11-01T01:30:00-04:00", "2026-11-01T01:30:00-05:00"])
def test_explicit_dst_offsets(value):
    assert normalize_datetime(value, ZoneInfo("America/New_York")).isoformat() == value


def test_available_alternative_providers():
    body = booking()
    client.post("/api/v1/appointments", json=body)
    response = client.post("/api/v1/appointments/availability", json={"preferred_date": "2026-11-10", "service_id": body["service_id"]})
    assert response.status_code == 200
    assert len({s["provider_id"] for s in response.json()["slots"]}) == 2
    assert response.json()["timezone"] == "America/New_York"


def test_cross_clinic_patient_is_rejected():
    with SessionLocal() as db:
        tenant = db.query(Clinic).first().tenant_id
        clinic = Clinic(tenant_id=tenant, name="Other")
        db.add(clinic); db.flush()
        patient = Patient(tenant_id=tenant, clinic_id=clinic.id, first_name="Other", last_name="Test")
        db.add(patient); db.commit()
    assert client.post("/api/v1/appointments", json=booking(patient_id=patient.id)).status_code == 404
