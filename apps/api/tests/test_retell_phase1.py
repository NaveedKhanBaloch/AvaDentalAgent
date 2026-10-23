import hashlib
import hmac
import json
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.core.config import get_settings
from app.models.models import (Appointment, Patient, Clinic, Provider, DentalService, RetellIntegration,
                               CallLog, FollowUp, WebhookEvent, IdempotencyRecord)

client = TestClient(app)
BASE = "/api/v1/integrations/retell"

@pytest.fixture
def context():
    with SessionLocal() as db:
        clinic = db.query(Clinic).first()
        provider = db.query(Provider).first()
        service = db.query(DentalService).filter(DentalService.default_duration_minutes == 30).first()
        integration = RetellIntegration(tenant_id=clinic.tenant_id, clinic_id=clinic.id, agent_id="agent_test", enabled=True)
        db.add(integration); db.commit()
        return {"provider_id": provider.id, "service_id": service.id, "clinic_id": clinic.id}


def signed_post(path, payload, signature=None, stamp=None):
    raw = json.dumps(payload, indent=2).encode()
    stamp = str(stamp or int(time.time()*1000))
    digest = hmac.new(get_settings().retell_api_key.encode(), raw + stamp.encode(), hashlib.sha256).hexdigest()
    return client.post(BASE + path, content=raw, headers={"content-type": "application/json",
        "x-retell-signature": signature or f"v={stamp},d={digest}"})


def tool(name, args, call_id="call_test", agent="agent_test"):
    return signed_post("/functions/" + name, {"name": name, "call": {"call_id": call_id, "agent_id": agent}, "args": args})


def book_args(context, **updates):
    return {**context, "first_name": "Synthetic", "last_name": "Patient", "phone": "+12025550123",
            "start_time": "2026-11-10T10:00:00-05:00", "confirmed": True, "idempotency_key": "booking-1", **updates}

@pytest.mark.parametrize("name", ["check_availability", "get_clinic_information", "get_treatment_information"])
def test_information_functions(context, name):
    body = tool(name, {**context, "preferred_date": "2026-11-10"}).json()
    assert body["success"] is True
    assert body["correlation_id"]

@pytest.mark.parametrize("name", ["lookup_patient", "verify-patient", "get_appointment", "reschedule_appointment", "cancel_appointment"])
def test_sensitive_functions_do_not_reveal_or_change(context, name):
    with SessionLocal() as db:
        patient = db.query(Patient).first()
        a = db.query(Appointment).first()
        original = (a.status, a.start_time)
    body = tool(name, {"patient_id": patient.id, "appointment_id": a.id, "phone": patient.phone, "confirmed": True}).json()
    assert body["status"] == "verification_required"
    assert "patient" not in body and "appointment" not in body
    with SessionLocal() as db:
        assert (db.get(Appointment, a.id).status, db.get(Appointment, a.id).start_time) == original


def test_booking_commit_idempotency_and_changed_key(context):
    args = book_args(context)
    first = tool("book_appointment", args)
    assert first.status_code == 200 and first.json()["success"], first.text
    again = tool("book_appointment", args).json()
    assert again["appointment_id"] == first.json()["appointment_id"]
    assert tool("book_appointment", {**args, "first_name": "Different"}).status_code == 409
    with SessionLocal() as db:
        assert db.query(Appointment).filter(Appointment.source == "retell").count() == 1
        assert db.query(IdempotencyRecord).count() == 1
        log = db.query(CallLog).filter(CallLog.external_call_id == "call_test").one()
        assert log.appointment_id == first.json()["appointment_id"]
        assert log.patient_id is None

@pytest.mark.parametrize("updates,status", [({"confirmed": False}, "confirmation_required"),
    ({"first_name": None}, "validation_error"), ({"confirmed": "true"}, "validation_error"),
    ({"patient_id": "untrusted"}, "verification_required"), ({"provider_id": "missing"}, "validation_error"),
    ({"idempotency_key": None}, "http_error")])
def test_booking_validation(context, updates, status):
    response = tool("book_appointment", book_args(context, **updates))
    if status == "http_error":
        assert response.status_code == 422
    else:
        assert response.json()["status"] == status
    with SessionLocal() as db:
        assert db.query(Appointment).filter(Appointment.source == "retell").count() == 0


def test_booking_conflict_is_structured(context):
    assert tool("book_appointment", book_args(context)).json()["success"]
    second = tool("book_appointment", book_args(context, idempotency_key="another"), call_id="other_call").json()
    assert second["status"] == "unavailable"
    with SessionLocal() as db:
        assert db.query(Patient).filter(Patient.first_name == "Synthetic").count() == 1


def test_invalid_context_and_args(context):
    assert tool("get_clinic_information", {}, agent="unknown").status_code == 403
    assert tool("get_clinic_information", {"clinic_id": "other"}).status_code == 403
    assert tool("get_clinic_information", []).status_code == 422


def test_signatures(context):
    payload = {"event": "call_ended", "call": {"agent_id": "agent_test", "call_id": "c"}}
    assert signed_post("/webhooks", payload, signature="invalid").status_code == 401
    assert signed_post("/webhooks", payload, stamp=int(time.time()*1000)-400000).status_code == 401
    assert signed_post("/webhooks", payload).status_code == 200


def test_webhook_dedup_out_of_order_no_booking(context):
    with SessionLocal() as db:
        original = db.query(Appointment).count()
    call = {"agent_id": "agent_test", "call_id": "event_call", "direction": "inbound", "from_number": "+12025550123",
            "start_timestamp": 1794300000000, "end_timestamp": 1794300060000}
    for event in ("call_analyzed", "call_started", "call_ended"):
        assert signed_post("/webhooks", {"event": event, "call": call}).json()["status"] == "accepted"
    assert signed_post("/webhooks", {"event": "call_ended", "call": call}).json()["status"] == "duplicate"
    with SessionLocal() as db:
        log = db.query(CallLog).filter(CallLog.external_call_id == "event_call").one()
        assert log.status == "analyzed" and log.duration == 60 and log.outcome == "unresolved"
        assert db.query(WebhookEvent).count() == 3
        assert db.query(Appointment).count() == original


def test_callback_real_and_idempotent(context):
    args = {"phone": "+12025550123", "reason": "Identity verification", "idempotency_key": "callback-1"}
    first = tool("create-followup", args).json()
    assert first["success"]
    assert tool("create-followup", args).json()["followup_id"] == first["followup_id"]
    with SessionLocal() as db:
        follow = db.get(FollowUp, first["followup_id"])
        assert follow.reason == args["reason"] and follow.patient_id is None


def test_unknown_event_and_missing_call(context):
    assert signed_post("/webhooks", {"event": "future_event", "call": {"agent_id": "agent_test"}}).json()["status"] == "ignored"
    assert signed_post("/webhooks", {"event": "call_started", "call": {"agent_id": "agent_test"}}).status_code == 422


def test_backend_temporary_failure(context, monkeypatch):
    from sqlalchemy.exc import OperationalError
    import app.api.v1.routes.retell as routes
    def fail(*args, **kwargs):
        raise OperationalError("query", {}, Exception("private database error"))
    monkeypatch.setattr(routes, "available_slots_for_day", fail)
    response = tool("check_availability", {"preferred_date": "2026-11-10"}).json()
    assert response["status"] == "temporary_failure"
    assert "private" not in str(response)
