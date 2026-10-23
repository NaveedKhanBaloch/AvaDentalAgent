import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.init_db import seed_demo_data
from app.db.session import SessionLocal
from app.main import app
from app.models.models import Appointment, CallLog, Clinic, DentalService, FollowUp, Membership, Patient, Provider, Tenant, User

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_demo_state() -> None:
    db = SessionLocal()
    for model in (FollowUp, Appointment, CallLog, Patient, Membership, Provider, DentalService, Clinic, User, Tenant):
        db.query(model).delete()
    db.commit()
    db.close()

    seed_demo_data()
    yield

    db = SessionLocal()
    for model in (FollowUp, Appointment, CallLog, Patient, Membership, Provider, DentalService, Clinic, User, Tenant):
        db.query(model).delete()
    db.commit()
    db.close()


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


def test_create_patient_accepts_blank_optional_fields() -> None:
    response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Noah",
            "last_name": "Brooks",
            "phone": "",
            "email": "",
            "preferred_contact_method": "phone",
            "notes": "",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["first_name"] == "Noah"
    assert body["last_name"] == "Brooks"
    assert body["phone"] is None
    assert body["email"] is None


def test_patient_search_update_and_delete() -> None:
    created = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Mia",
            "last_name": "Rodriguez",
            "phone": "555-0123",
            "email": "mia@example.com",
            "preferred_contact_method": "text",
            "notes": "Needs follow-up",
        },
    )
    assert created.status_code == 201, created.text
    patient_id = created.json()["id"]

    searched = client.get("/api/v1/patients?search=Rodriguez")
    assert searched.status_code == 200, searched.text
    assert any(item["id"] == patient_id for item in searched.json()["items"])

    updated = client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"first_name": "Mia", "last_name": "Lopez", "notes": "Updated note"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["last_name"] == "Lopez"

    deleted = client.delete(f"/api/v1/patients/{patient_id}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] is True


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


def test_create_appointment_from_dashboard_flow() -> None:
    patient = client.get("/api/v1/patients")
    patient_id = patient.json()["items"][0]["id"]
    provider = client.get("/api/v1/providers")
    service = client.get("/api/v1/services")

    response = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "provider_id": provider.json()["items"][0]["id"],
            "service_id": service.json()["items"][0]["id"],
            "start_time": "2026-11-12T10:30:00+00:00",
            "end_time": "2026-11-12T11:15:00+00:00",
            "status": "scheduled",
            "source": "dashboard",
            "notes": "Follow-up from front desk.",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "created"
    assert body["appointment_id"]


def test_operations_queue_is_available() -> None:
    calls = client.get("/api/v1/operations/calls")
    assert calls.status_code == 200, calls.text
    assert "items" in calls.json()

    follow_ups = client.get("/api/v1/operations/follow-ups")
    assert follow_ups.status_code == 200, follow_ups.text
    assert "items" in follow_ups.json()


def test_staff_roles_are_exposed() -> None:
    response = client.get("/api/v1/staff")
    assert response.status_code == 200, response.text
    body = response.json()
    assert "items" in body
    assert len(body["items"]) >= 1
    assert "permissions" in body["items"][0]


def test_appointment_lifecycle_update() -> None:
    patients = client.get("/api/v1/patients")
    patient = patients.json()["items"][0]
    providers = client.get("/api/v1/providers")
    provider = providers.json()["items"][0]
    service = client.get("/api/v1/services").json()["items"][0]

    created = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "provider_id": provider["id"],
            "service_id": service["id"],
            "start_time": "2026-11-20T09:00:00+00:00",
            "end_time": "2026-11-20T09:45:00+00:00",
            "status": "scheduled",
            "source": "dashboard",
            "notes": "Follow-up from community outreach.",
        },
    )
    appointment_id = created.json()["appointment_id"]

    response = client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        json={"status": "confirmed", "notes": "Confirmed with patient by phone."},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["notes"] == "Confirmed with patient by phone."


def test_provider_conflict_rejected() -> None:
    patients = client.get("/api/v1/patients")
    patient = patients.json()["items"][0]
    providers = client.get("/api/v1/providers")
    provider = providers.json()["items"][0]

    first = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "provider_id": provider["id"],
            "service_id": client.get("/api/v1/services").json()["items"][0]["id"],
            "start_time": "2026-11-18T10:00:00+00:00",
            "end_time": "2026-11-18T10:45:00+00:00",
            "status": "scheduled",
            "source": "dashboard",
            "notes": "Initial booking.",
        },
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "provider_id": provider["id"],
            "service_id": client.get("/api/v1/services").json()["items"][0]["id"],
            "start_time": "2026-11-18T10:15:00+00:00",
            "end_time": "2026-11-18T11:00:00+00:00",
            "status": "scheduled",
            "source": "dashboard",
            "notes": "Overlap should be blocked.",
        },
    )
    assert second.status_code == 409, second.text
    assert "overlap" in second.json()["detail"].lower()


def test_manual_booking_can_be_updated_and_deleted() -> None:
    patients = client.get("/api/v1/patients")
    patient = patients.json()["items"][0]
    providers = client.get("/api/v1/providers")
    provider = providers.json()["items"][0]
    service = client.get("/api/v1/services").json()["items"][0]

    created = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient["id"],
            "provider_id": provider["id"],
            "service_id": service["id"],
            "start_time": "2026-11-22T08:00:00+00:00",
            "end_time": "2026-11-22T08:30:00+00:00",
            "status": "scheduled",
            "source": "manual",
            "notes": "Manual booking created.",
        },
    )
    appointment_id = created.json()["appointment_id"]

    updated = client.patch(
        f"/api/v1/appointments/{appointment_id}",
        json={
            "start_time": "2026-11-22T08:30:00+00:00",
            "end_time": "2026-11-22T09:00:00+00:00",
            "status": "confirmed",
            "notes": "Updated by front desk.",
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["status"] == "confirmed"
    assert body["notes"] == "Updated by front desk."

    deleted = client.delete(f"/api/v1/appointments/{appointment_id}")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "cancelled"


def test_retell_webhook_creates_booking() -> None:
    provider = client.get("/api/v1/providers").json()["items"][0]
    service = client.get("/api/v1/services").json()["items"][0]

    response = client.post(
        "/api/v1/integrations/retell/webhooks",
        json={
            "patient": {
                "first_name": "Ariana",
                "last_name": "Nguyen",
                "phone": "555-0199",
                "email": "ariana@example.com",
            },
            "provider_id": provider["id"],
            "service_id": service["id"],
            "start_time": "2026-11-24T11:00:00+00:00",
            "end_time": "2026-11-24T11:45:00+00:00",
            "source": "retell",
            "notes": "AI booking from inbound call.",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert body["appointment_id"]


def test_provider_calendar_block_and_insurance_intake() -> None:
    patient = client.get("/api/v1/patients").json()["items"][0]
    provider = client.get("/api/v1/providers").json()["items"][0]

    block_response = client.post(
        f"/api/v1/providers/{provider['id']}/calendar/blocks",
        json={
            "start_time": "2026-11-25T13:00:00+00:00",
            "end_time": "2026-11-25T15:00:00+00:00",
            "reason": "Continuing education",
            "exception_type": "time_off",
        },
    )
    assert block_response.status_code == 200, block_response.text
    assert block_response.json()["reason"] == "Continuing education"

    calendar_response = client.get(f"/api/v1/providers/{provider['id']}/calendar?date=2026-11-25")
    assert calendar_response.status_code == 200, calendar_response.text
    assert any(item["reason"] == "Continuing education" for item in calendar_response.json()["blocks"])

    insurance_response = client.post(
        f"/api/v1/patients/{patient['id']}/insurance",
        json={
            "carrier_name": "BlueCross BlueShield",
            "policy_number": "ABC-12345",
            "group_number": "GRP-77",
            "member_name": patient["first_name"] + " " + patient["last_name"],
            "subscriber_dob": "1990-04-15",
            "relationship_to_patient": "self",
            "status": "pending",
            "notes": "Primary insurance verification pending.",
        },
    )
    assert insurance_response.status_code == 201, insurance_response.text
    assert insurance_response.json()["carrier_name"] == "BlueCross BlueShield"


def test_non_owner_cannot_block_provider_calendar() -> None:
    db = SessionLocal()
    role_user = User(
        email="dentist.demo@example.com",
        password_hash=hash_password("SecurePass123!"),
        full_name="Dr. Smith",
        status="active",
    )
    db.add(role_user)
    db.flush()

    tenant = db.query(Membership).first()
    if tenant is None:
        tenant = Membership(user_id=role_user.id, tenant_id="demo-tenant", clinic_id="demo-clinic", role="dentist", status="active")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)
    else:
        db.add(Membership(user_id=role_user.id, tenant_id="demo-tenant", clinic_id="demo-clinic", role="dentist", status="active"))
        db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "dentist.demo@example.com", "password": "SecurePass123!"},
    )
    assert login.status_code == 200, login.text

    provider = client.get("/api/v1/providers").json()["items"][0]
    response = client.post(
        f"/api/v1/providers/{provider['id']}/calendar/blocks",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={
            "start_time": "2026-11-28T09:00:00+00:00",
            "end_time": "2026-11-28T10:00:00+00:00",
            "reason": "Clinical education",
            "exception_type": "time_off",
        },
    )
    assert response.status_code == 403, response.text
    assert "permission" in response.json()["detail"].lower()
