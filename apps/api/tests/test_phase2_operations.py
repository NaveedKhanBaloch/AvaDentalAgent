from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import Patient, ReminderPreparation

client = TestClient(app)


def patient():
    return client.get("/api/v1/patients").json()["items"][0]["id"]


def test_followup_lifecycle_assignment_and_revision():
    r = client.post(
        "/api/v1/operations/follow-ups",
        json={"patient_id": patient(), "reason": "Callback", "due_at": "2020-01-01T00:00:00Z"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    body = {k: data[k] for k in ["patient_id", "reason", "due_at"]}
    body.update(expected_revision=1, status="completed")
    r = client.patch("/api/v1/operations/follow-ups/" + data["id"], json=body)
    assert r.status_code == 200 and r.json()["completed_at"]
    assert client.patch("/api/v1/operations/follow-ups/" + data["id"], json=body).status_code == 409
    assert (
        client.post(
            "/api/v1/operations/follow-ups",
            json={"patient_id": patient(), "reason": "Invalid", "assigned_user_id": "other"},
        ).status_code
        == 422
    )


def test_recall_distinct_and_contact_opt_out():
    pid = patient()
    r = client.post(
        "/api/v1/operations/recalls",
        json={"patient_id": pid, "recall_type": "Clinician requested", "due_date": "2020-01-01"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "due"
    client.patch("/api/v1/patients/" + pid, json={"do_not_contact": True})
    body = {
        "patient_id": pid,
        "recall_type": "Clinician requested",
        "due_date": "2020-01-01",
        "status": "contacted",
        "log_contact_attempt": True,
        "expected_revision": 1,
    }
    assert client.patch("/api/v1/operations/recalls/" + data["id"], json=body).status_code == 409
    first = client.post("/api/v1/operations/reminders/prepare").json()
    assert first["messages_sent"] == 0
    assert client.post("/api/v1/operations/reminders/prepare").json()["processed"] == 0
    with SessionLocal() as db:
        assert db.query(ReminderPreparation).count() == 1
        assert db.query(ReminderPreparation).first().status == "suppressed"


def test_followup_allows_unverified_callback():
    r = client.post(
        "/api/v1/operations/follow-ups",
        json={"contact_phone": "+12025550123", "reason": "Verify identity"},
    )
    assert r.status_code == 201 and r.json()["patient_id"] is None


def test_approved_recall_rule_date_and_completion():
    from datetime import datetime, timedelta, timezone
    from app.models.models import Appointment, Provider, DentalService, Clinic

    token = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@harbordentaldemo.local", "password": "AdminPass123!"},
    ).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    rule = client.post(
        "/api/v1/operations/recall-rules",
        headers=headers,
        json={
            "name": "Synthetic approved interval",
            "interval_days": 90,
            "clinically_approved": True,
        },
    )
    assert rule.status_code == 201, rule.text
    pid = patient()
    with SessionLocal() as db:
        p = db.get(Patient, pid)
        provider = db.query(Provider).first()
        service = db.query(DentalService).first()
        start = datetime(2020, 1, 6, 12, tzinfo=timezone.utc)
        a = Appointment(
            tenant_id=p.tenant_id,
            clinic_id=p.clinic_id,
            patient_id=pid,
            provider_id=provider.id,
            service_id=service.id,
            start_time=start,
            end_time=start + timedelta(minutes=30),
            status="completed",
        )
        db.add(a)
        db.commit()
        aid = a.id
    body = {
        "patient_id": pid,
        "recall_type": "Synthetic review",
        "recall_rule_id": rule.json()["id"],
        "origin_appointment_id": aid,
    }
    r = client.post("/api/v1/operations/recalls", json=body)
    assert r.status_code == 201, r.text
    recall = r.json()
    assert recall["due_date"] == "2020-04-05"
    # Cannot falsely claim scheduled using a completed appointment.
    assert (
        client.patch(
            "/api/v1/operations/recalls/" + recall["id"],
            json={**body, "appointment_id": aid, "expected_revision": 1, "status": "scheduled"},
        ).status_code
        == 422
    )
    # Terminal transition cannot skip the contact/scheduling workflow.
    assert (
        client.patch(
            "/api/v1/operations/recalls/" + recall["id"],
            json={
                **body,
                "expected_revision": 1,
                "status": "completed",
                "completion_reason": "Admin",
            },
        ).status_code
        == 409
    )


def test_consent_revocation_suppresses_existing_preparation():
    pid = patient()
    assert (
        client.patch(
            "/api/v1/patients/" + pid,
            json={
                "email": "synthetic@example.com",
                "email_consent": True,
                "preferred_contact_method": "email",
            },
        ).status_code
        == 200
    )
    r = client.post(
        "/api/v1/operations/follow-ups",
        json={
            "patient_id": pid,
            "reason": "Synthetic consent check",
            "due_at": "2020-01-01T00:00:00Z",
        },
    )
    assert r.status_code == 201
    assert client.post("/api/v1/operations/reminders/prepare").json()["processed"] == 1
    with SessionLocal() as db:
        assert db.query(ReminderPreparation).first().status == "prepared"
    client.patch("/api/v1/patients/" + pid, json={"email_consent": False})
    assert client.post("/api/v1/operations/reminders/prepare").json()["processed"] == 0
    with SessionLocal() as db:
        assert db.query(ReminderPreparation).first().status == "suppressed"


def test_operations_roles_and_cross_clinic_isolation():
    from app.models.models import User, Membership, Tenant, Clinic
    from app.core.security import create_access_token

    pid = patient()
    r = client.post(
        "/api/v1/operations/follow-ups",
        json={"patient_id": pid, "reason": "Synthetic scoped follow-up"},
    ).json()
    with SessionLocal() as db:
        clinic = db.query(Clinic).first()
        dentist = User(
            email="dentist-synthetic@example.com",
            full_name="Synthetic dentist",
            password_hash="unused",
        )
        db.add(dentist)
        db.flush()
        db.add(
            Membership(
                user_id=dentist.id, clinic_id=clinic.id, tenant_id=clinic.tenant_id, role="dentist"
            )
        )
        tenant = Tenant(name="Other synthetic", slug="operations-other")
        db.add(tenant)
        db.flush()
        other = Clinic(name="Other synthetic", tenant_id=tenant.id)
        db.add(other)
        db.flush()
        user = User(email="other-operations@example.com", full_name="Other", password_hash="unused")
        db.add(user)
        db.flush()
        db.add(
            Membership(
                user_id=user.id, clinic_id=other.id, tenant_id=tenant.id, role="clinic_owner"
            )
        )
        db.commit()
    dentist_headers = {"Authorization": "Bearer " + create_access_token(dentist.id)}
    other_headers = {"Authorization": "Bearer " + create_access_token(user.id)}
    assert client.get("/api/v1/operations/follow-ups", headers=dentist_headers).status_code == 200
    assert (
        client.post(
            "/api/v1/operations/follow-ups",
            headers=dentist_headers,
            json={"patient_id": pid, "reason": "Forbidden"},
        ).status_code
        == 403
    )
    assert (
        client.get("/api/v1/operations/follow-ups/" + r["id"], headers=other_headers).status_code
        == 404
    )
    assert (
        client.get("/api/v1/patients/" + pid + "/timeline", headers=other_headers).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/operations/recalls",
            headers=other_headers,
            json={"patient_id": pid, "recall_type": "Forbidden", "due_date": "2026-01-01"},
        ).status_code
        == 404
    )
