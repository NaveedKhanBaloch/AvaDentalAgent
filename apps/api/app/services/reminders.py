"""Sandbox-only preparation. No transport, message content or patient contact is emitted."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models.models import FollowUp, Patient, Recall, ReminderPreparation
from app.services.patient_operations import event
from app.services.retell import transaction_lock


def prepare_reminders(db, clinic):
    transaction_lock(db, "reminder-preparation:" + clinic.id)
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo(clinic.timezone or "UTC")).date()
    processed = 0
    for kind, model in [("followup", FollowUp), ("recall", Recall)]:
        query = db.query(model).filter(
            model.clinic_id == clinic.id, ~model.status.in_(["completed", "cancelled"])
        )
        query = (
            query.filter(FollowUp.due_at <= now)
            if kind == "followup"
            else query.filter(Recall.due_date <= today)
        )
        cursor = ""
        while True:
            rows = query.filter(model.id > cursor).order_by(model.id).limit(500).all()
            if not rows:
                break
            cursor = rows[-1].id
            patients = {
                p.id: p
                for p in db.query(Patient).filter(
                    Patient.clinic_id == clinic.id,
                    Patient.id.in_([r.patient_id for r in rows if r.patient_id]),
                )
            }
            preparations = {
                (r.entity_id, r.revision, r.channel): r
                for r in db.query(ReminderPreparation).filter(
                    ReminderPreparation.clinic_id == clinic.id,
                    ReminderPreparation.entity_type == kind,
                    ReminderPreparation.entity_id.in_([r.id for r in rows]),
                )
            }
            for row in rows:
                patient = patients.get(row.patient_id)
                channel = (
                    row.contact_preference
                    if kind == "recall"
                    else patient.preferred_contact_method if patient else "phone"
                )
                if channel == "text":
                    channel = "sms"
                allowed = bool(
                    patient
                    and patient.status == "active"
                    and not patient.do_not_contact
                    and (
                        (channel == "email" and patient.email_consent and patient.email)
                        or (channel == "sms" and patient.sms_consent and patient.phone)
                    )
                )
                existing = preparations.get((row.id, row.revision, channel))
                if existing:
                    if not allowed and existing.status == "prepared":
                        existing.status = "suppressed"
                        existing.reason = "Consent or patient status no longer permits contact"
                    continue
                record = ReminderPreparation(
                    clinic_id=clinic.id,
                    entity_type=kind,
                    entity_id=row.id,
                    revision=row.revision,
                    channel=channel,
                    status="prepared" if allowed else "suppressed",
                    reason=(
                        "Sandbox only; no communication sent"
                        if allowed
                        else "Consent, channel or patient status blocks preparation"
                    ),
                )
                db.add(record)
                db.flush()
                event(db, clinic, "reminder." + record.status, record, row.patient_id)
                processed += 1
    db.commit()
    return {"processed": processed, "transport": "sandbox", "messages_sent": 0}
