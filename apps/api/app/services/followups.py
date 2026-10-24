from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.authorization import request_user
from app.models.models import Appointment, CallLog, FollowUp, Patient, Recall, RecallRule
from app.services.patient_operations import check_assignment, check_revision, event, scoped

FOLLOW_TRANSITIONS = {
    "pending": {"in_progress", "completed", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
RECALL_TRANSITIONS = {
    "due": {"contact_pending", "contacted", "scheduled", "cancelled"},
    "contact_pending": {"contacted", "scheduled", "cancelled"},
    "contacted": {"contact_pending", "scheduled", "cancelled"},
    "scheduled": {"completed", "contact_pending", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def serialize(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def save_operation(db, clinic, data, kind="followup", record=None, integration_actor=None):
    values = dict(data)
    expected = values.pop("expected_revision", None)
    log_attempt = values.pop("log_contact_attempt", False)
    model = FollowUp if kind == "followup" else Recall
    creating = record is None
    if record:
        check_revision(record, expected)
    target = values.pop(
        "status", record.status if record else ("pending" if kind == "followup" else "due")
    )
    if (
        record
        and target != record.status
        and target
        not in (FOLLOW_TRANSITIONS if kind == "followup" else RECALL_TRANSITIONS).get(
            record.status, set()
        )
    ):
        raise HTTPException(409, "Invalid status transition")
    patient_id = values.get("patient_id", record.patient_id if record else None)
    patient = scoped(db, Patient, patient_id, clinic) if patient_id else None
    if creating and patient and patient.status != "active":
        raise HTTPException(409, "Restore archived patient before creating operational records")
    if kind == "recall" and not patient:
        raise HTTPException(422, "Patient is required")
    if (
        kind == "followup"
        and not patient
        and not values.get("contact_phone", getattr(record, "contact_phone", None))
    ):
        raise HTTPException(422, "Patient or callback phone is required")
    check_assignment(db, clinic, values.get("assigned_user_id"))
    for field, related in [
        ("appointment_id", Appointment),
        ("origin_appointment_id", Appointment),
        ("call_id", CallLog),
    ]:
        rid = values.get(field)
        if rid:
            related_row = scoped(db, related, rid, clinic)
            if patient_id and related_row.patient_id != patient_id:
                raise HTTPException(422, "Related record must belong to the selected patient")
            if field == "origin_appointment_id" and related_row.status != "completed":
                raise HTTPException(422, "Recall origin appointment must be completed")
    if values.get("estimate_id"):
        from app.models.models import TreatmentEstimate

        estimate = scoped(db, TreatmentEstimate, values["estimate_id"], clinic)
        if estimate.patient_id != patient_id:
            raise HTTPException(422, "Estimate must belong to patient")
    if kind == "recall":
        if values.get("recall_rule_id"):
            rule = scoped(db, RecallRule, values["recall_rule_id"], clinic)
            origin = scoped(db, Appointment, values.get("origin_appointment_id"), clinic)
            if origin.patient_id != patient_id or origin.status != "completed":
                raise HTTPException(
                    422,
                    "An approved interval requires a completed origin appointment for this patient",
                )
            from datetime import timedelta
            from zoneinfo import ZoneInfo

            from app.services.scheduling import stored_datetime

            values["due_date"] = stored_datetime(origin.end_time).astimezone(
                ZoneInfo(clinic.timezone or "UTC")
            ).date() + timedelta(days=rule.interval_days)
        if not values.get("due_date", getattr(record, "due_date", None)):
            raise HTTPException(422, "An approved due date or interval rule is required")
        aid = values.get("appointment_id", record.appointment_id if record else None)
        if target == "scheduled":
            if not aid:
                raise HTTPException(422, "Scheduled recall requires an appointment")
            a = scoped(db, Appointment, aid, clinic)
            if a.patient_id != patient_id or a.status not in {
                "scheduled",
                "confirmed",
                "checked_in",
            }:
                raise HTTPException(422, "Recall needs an active appointment for this patient")
        if target == "completed" and not values.get("completion_reason"):
            a = scoped(db, Appointment, aid, clinic) if aid else None
            if not a or a.status != "completed":
                raise HTTPException(
                    422,
                    "Completion requires a completed appointment or administrative completion reason",
                )
        if log_attempt and (patient.do_not_contact or patient.status != "active"):
            raise HTTPException(409, "Contact is blocked by patient preference or archive status")
    user = request_user.get()
    if creating:
        record = model(
            tenant_id=clinic.tenant_id,
            clinic_id=clinic.id,
            created_by=user.id if user else integration_actor,
        )
        db.add(record)
    for key, value in values.items():
        setattr(record, key, value)
    if log_attempt:
        record.last_contact_at = datetime.now(timezone.utc)
    if target == "completed" and record.status != "completed":
        record.completed_at = datetime.now(timezone.utc)
        record.completed_by = user.id if user else integration_actor
    record.status = target
    if not creating:
        record.revision += 1
    db.flush()
    event(
        db,
        clinic,
        f'{kind}.{"created" if creating else target if target in {"completed","cancelled"} else "updated"}',
        record,
        patient_id,
        values,
    )
    return record
