"""Shared clinic scope, safe event audit and bounded administrative projections."""

from fastapi import HTTPException
from sqlalchemy import and_, exists, func, literal, select, union_all

from app.core.audit import write_audit_event
from app.core.authorization import capabilities, request_user
from app.models.models import Appointment, AuditLog, CallLog, FollowUp, Membership, Patient


def scoped(db, model, record_id, clinic, lock=False):
    query = db.query(model).filter(model.id == record_id, model.clinic_id == clinic.id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    record = query.first()
    if not record:
        raise HTTPException(404, "Record not found")
    return record


def event(db, clinic, action, entity, patient_id=None, changed=None):
    user = request_user.get()
    return write_audit_event(
        db,
        tenant_id=clinic.tenant_id,
        clinic_id=clinic.id,
        patient_id=patient_id,
        action=action,
        entity_type=entity.__tablename__,
        entity_id=entity.id,
        actor_type="user" if user else "system",
        actor_id=user.id if user else None,
        metadata={"changed_fields": sorted(changed or [])},
    )


def check_revision(record, expected):
    if expected is not None and expected != record.revision:
        raise HTTPException(409, "Record changed. Reload and review before saving.")


def check_assignment(db, clinic, user_id):
    if (
        user_id
        and not db.query(Membership)
        .filter_by(clinic_id=clinic.id, user_id=user_id, status="active")
        .first()
    ):
        raise HTTPException(422, "Assigned staff must be an active clinic member")


def patient_dict(p):
    return {
        k: getattr(p, k)
        for k in (
            "id",
            "first_name",
            "last_name",
            "phone",
            "email",
            "notes",
            "preferred_contact_method",
            "created_at",
            "date_of_birth",
            "status",
            "do_not_contact",
            "email_consent",
            "sms_consent",
            "revision",
            "updated_at",
            "archived_at",
        )
    }


def page_query(query, page=1, page_size=25):
    total = query.order_by(None).count()
    return query.offset((page - 1) * page_size).limit(page_size).all(), total


def timeline(db, clinic, patient, page, size):
    # SQL UNION is paginated in the database; no full-history Python slicing.
    def source(model, when, kind, actor, condition):
        return select(
            model.id.label("id"),
            when.label("timestamp"),
            literal(kind).label("event_type"),
            actor.label("actor"),
            model.id.label("related_id"),
        ).where(condition)

    audited = select(
        AuditLog.id.label("id"),
        AuditLog.timestamp.label("timestamp"),
        AuditLog.action.label("event_type"),
        func.coalesce(AuditLog.actor_id, AuditLog.actor_type).label("actor"),
        AuditLog.entity_id.label("related_id"),
    ).where(
        AuditLog.tenant_id == clinic.tenant_id,
        AuditLog.clinic_id == clinic.id,
        AuditLog.patient_id == patient.id,
    )
    if "estimate_read" not in capabilities(db):
        audited = audited.where(~AuditLog.action.like("estimate.%"))
    queries = [audited]

    def no_audit(model):
        return ~exists(
            select(AuditLog.id).where(
                AuditLog.entity_id == model.id,
                AuditLog.clinic_id == clinic.id,
                AuditLog.patient_id == patient.id,
            )
        )

    queries.append(
        source(
            Patient,
            Patient.created_at,
            "patient.registered",
            literal("system"),
            and_(Patient.id == patient.id, no_audit(Patient)),
        )
    )
    queries.append(
        source(
            Appointment,
            Appointment.created_at,
            "appointment.created",
            Appointment.source,
            and_(
                Appointment.clinic_id == clinic.id,
                Appointment.patient_id == patient.id,
                no_audit(Appointment),
            ),
        )
    )
    queries.append(
        source(
            FollowUp,
            FollowUp.created_at,
            "follow_up.created",
            literal("system"),
            and_(
                FollowUp.clinic_id == clinic.id,
                FollowUp.patient_id == patient.id,
                no_audit(FollowUp),
            ),
        )
    )
    queries.append(
        source(
            CallLog,
            CallLog.created_at,
            "call.recorded",
            literal("integration"),
            and_(CallLog.clinic_id == clinic.id, CallLog.patient_id == patient.id),
        )
    )
    combined = union_all(*queries).subquery()
    total = db.scalar(select(func.count()).select_from(combined))
    rows = (
        db.execute(
            select(combined)
            .order_by(combined.c.timestamp.desc(), combined.c.event_type, combined.c.id)
            .offset((page - 1) * size)
            .limit(size)
        )
        .mappings()
        .all()
    )
    return {
        "items": [
            dict(r, description=r["event_type"].replace("_", " ").replace(".", " · ")) for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": size,
    }
