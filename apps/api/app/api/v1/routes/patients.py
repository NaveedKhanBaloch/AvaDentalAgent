from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, StrictBool
from sqlalchemy import or_, func, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.authorization import get_user_default_clinic, require_permission, request_user
from app.db.session import get_db
from app.models.models import (
    Clinic,
    Tenant,
    User,
    Patient,
    Appointment,
    InsuranceProfile,
    CallLog,
    FollowUp,
)
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.patient_operations import (
    scoped,
    event,
    check_revision,
    patient_dict,
    page_query,
    timeline,
)

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
    dependencies=[Depends(require_permission("patient_read"))],
)


class InsuranceCreate(BaseModel):
    carrier_name: str
    policy_number: str | None = None
    group_number: str | None = None
    member_name: str | None = None
    subscriber_dob: str | None = None
    relationship_to_patient: str | None = None
    status: str = "pending"
    notes: str | None = None


def get_default_tenant_and_clinic(db, user=None):
    return get_user_default_clinic(db, user)


@router.get("")
def list_patients(
    search: str | None = None,
    patient_status: str | None = Query(default=None, alias="status"),
    sort: str = "created_at",
    direction: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    registered_from: datetime | None = None,
    registered_to: datetime | None = None,
    db: Session = Depends(get_db),
):
    _, clinic = get_default_tenant_and_clinic(db)
    now = datetime.now(timezone.utc)
    history = (
        db.query(
            Appointment.patient_id,
            func.max(case((Appointment.status == "completed", Appointment.start_time))).label(
                "last_appointment"
            ),
            func.min(
                case(
                    (
                        (Appointment.start_time >= now)
                        & Appointment.status.in_(["scheduled", "confirmed"]),
                        Appointment.start_time,
                    )
                )
            ).label("next_appointment"),
        )
        .filter(Appointment.clinic_id == clinic.id)
        .group_by(Appointment.patient_id)
        .subquery()
    )
    query = (
        db.query(Patient, history.c.last_appointment, history.c.next_appointment)
        .outerjoin(history, Patient.id == history.c.patient_id)
        .filter(Patient.clinic_id == clinic.id)
    )
    if search:
        term = "%" + search.strip() + "%"
        query = query.filter(
            or_(
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                Patient.email.ilike(term),
                Patient.phone.ilike(term),
            )
        )
    if patient_status:
        if patient_status not in {"active", "archived"}:
            raise HTTPException(422, "Unknown patient status")
        query = query.filter(Patient.status == patient_status)
    if registered_from:
        query = query.filter(Patient.created_at >= registered_from)
    if registered_to:
        query = query.filter(Patient.created_at <= registered_to)
    sorts = {
        "created_at": Patient.created_at,
        "name": Patient.last_name,
        "last_appointment": history.c.last_appointment,
    }
    if sort not in sorts or direction not in {"asc", "desc"}:
        raise HTTPException(422, "Invalid sorting")
    column = sorts[sort]
    rows, total = page_query(
        query.order_by(column.asc() if direction == "asc" else column.desc(), Patient.id),
        page,
        page_size,
    )
    return {
        "items": [
            dict(patient_dict(p), last_appointment=last, next_appointment=nxt)
            for p, last, nxt in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201, dependencies=[Depends(require_permission("patient_write"))])
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    patient = Patient(tenant_id=clinic.tenant_id, clinic_id=clinic.id, **payload.model_dump())
    if patient.email:
        patient.email = str(patient.email)
    db.add(patient)
    db.flush()
    event(db, clinic, "patient.registered", patient, patient.id)
    db.commit()
    return patient_dict(patient)


@router.get("/{patient_id}")
@router.get("/{patient_id}/profile")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    p = scoped(db, Patient, patient_id, clinic)
    return dict(
        patient_dict(p),
        tenant_id=p.tenant_id,
        clinic_id=p.clinic_id,
        last_appointment=db.query(func.max(Appointment.start_time))
        .filter(
            Appointment.clinic_id == clinic.id,
            Appointment.patient_id == p.id,
            Appointment.status == "completed",
        )
        .scalar(),
        next_appointment=db.query(func.min(Appointment.start_time))
        .filter(
            Appointment.clinic_id == clinic.id,
            Appointment.patient_id == p.id,
            Appointment.status.in_(["scheduled", "confirmed", "checked_in"]),
            Appointment.start_time >= datetime.now(timezone.utc),
        )
        .scalar(),
        open_followups=db.query(FollowUp)
        .filter(
            FollowUp.clinic_id == clinic.id,
            FollowUp.patient_id == p.id,
            FollowUp.status.in_(["pending", "in_progress"]),
        )
        .count(),
    )


@router.patch("/{patient_id}", dependencies=[Depends(require_permission("patient_write"))])
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    p = scoped(db, Patient, patient_id, clinic, True)
    check_revision(p, payload.expected_revision)
    changes = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
    for key, value in changes.items():
        if (
            key
            in {
                "first_name",
                "last_name",
                "preferred_contact_method",
                "do_not_contact",
                "email_consent",
                "sms_consent",
            }
            and value is None
        ):
            raise HTTPException(422, "Required patient fields cannot be cleared")
        setattr(p, key, str(value) if key == "email" and value else value)
    p.revision += 1
    event(db, clinic, "patient.updated", p, p.id, changes)
    db.commit()
    return patient_dict(p)


class ArchiveAction(BaseModel):
    confirmed: StrictBool
    expected_revision: int = Field(ge=1)


@router.post("/{patient_id}/archive", dependencies=[Depends(require_permission("patient_archive"))])
@router.post("/{patient_id}/restore", dependencies=[Depends(require_permission("patient_archive"))])
def archive_patient(
    patient_id: str, payload: ArchiveAction, request: Request, db: Session = Depends(get_db)
):
    if not payload.confirmed:
        raise HTTPException(422, "Explicit confirmation required")
    _, clinic = get_default_tenant_and_clinic(db)
    p = scoped(db, Patient, patient_id, clinic, True)
    check_revision(p, payload.expected_revision)
    archive = request.url.path.endswith("/archive")
    p.status = "archived" if archive else "active"
    p.archived_at = datetime.now(timezone.utc) if archive else None
    p.archived_by = request_user.get().id if archive and request_user.get() else None
    p.revision += 1
    event(db, clinic, "patient.archived" if archive else "patient.restored", p, p.id)
    db.commit()
    return patient_dict(p)


@router.delete("/{patient_id}", dependencies=[Depends(require_permission("patient_delete"))])
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    p = scoped(db, Patient, patient_id, clinic, True)
    for model in (Appointment, InsuranceProfile, FollowUp, CallLog):
        if db.query(model).filter(model.patient_id == p.id).first():
            raise HTTPException(409, "Patient has retained related records; archive instead")
    # Estimates and recalls are checked once their models are registered.
    from app.models import models

    for name in ("Recall", "TreatmentEstimate"):
        model = getattr(models, name, None)
        if model is not None and db.query(model).filter(model.patient_id == p.id).first():
            raise HTTPException(409, "Patient has retained related records; archive instead")
    event(db, clinic, "patient.deleted", p, p.id)
    db.delete(p)
    db.commit()
    return {"id": patient_id, "deleted": True}


@router.get("/{patient_id}/timeline")
def patient_timeline(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _, clinic = get_default_tenant_and_clinic(db)
    p = scoped(db, Patient, patient_id, clinic)
    return timeline(db, clinic, p, page, page_size)


@router.get("/{patient_id}/appointments")
def patient_appointments(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _, clinic = get_default_tenant_and_clinic(db)
    scoped(db, Patient, patient_id, clinic)
    rows, total = page_query(
        db.query(Appointment)
        .filter_by(clinic_id=clinic.id, patient_id=patient_id)
        .order_by(Appointment.start_time.desc()),
        page,
        page_size,
    )
    from app.api.v1.routes.scheduler import serialize

    return {
        "items": [serialize(a, clinic) for a in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{patient_id}/communications")
def patient_calls(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _, clinic = get_default_tenant_and_clinic(db)
    scoped(db, Patient, patient_id, clinic)
    rows, total = page_query(
        db.query(CallLog)
        .filter_by(clinic_id=clinic.id, patient_id=patient_id)
        .order_by(CallLog.created_at.desc()),
        page,
        page_size,
    )
    return {
        "items": [
            {"id": r.id, "status": r.status, "outcome": r.outcome, "created_at": r.created_at}
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{patient_id}/insurance")
def get_patient_insurance(patient_id: str, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    scoped(db, Patient, patient_id, clinic)
    rows = (
        db.query(InsuranceProfile)
        .filter_by(clinic_id=clinic.id, patient_id=patient_id)
        .order_by(InsuranceProfile.created_at.desc())
        .all()
    )
    return {
        "items": [
            {c.name: getattr(r, c.name) for c in InsuranceProfile.__table__.columns} for r in rows
        ]
    }


@router.post(
    "/{patient_id}/insurance",
    status_code=201,
    dependencies=[Depends(require_permission("patient_write"))],
)
def create_patient_insurance(
    patient_id: str, payload: InsuranceCreate, db: Session = Depends(get_db)
):
    _, clinic = get_default_tenant_and_clinic(db)
    scoped(db, Patient, patient_id, clinic)
    r = InsuranceProfile(
        tenant_id=clinic.tenant_id,
        clinic_id=clinic.id,
        patient_id=patient_id,
        **payload.model_dump(),
    )
    db.add(r)
    db.flush()
    event(db, clinic, "insurance.created", r, patient_id)
    db.commit()
    return {c.name: getattr(r, c.name) for c in InsuranceProfile.__table__.columns}


@router.get("/{patient_id}/follow-ups")
def patient_followups(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _, clinic = get_default_tenant_and_clinic(db)
    scoped(db, Patient, patient_id, clinic)
    rows, total = page_query(
        db.query(FollowUp)
        .filter_by(clinic_id=clinic.id, patient_id=patient_id)
        .order_by(FollowUp.created_at.desc()),
        page,
        page_size,
    )
    return {
        "items": [
            {k: getattr(r, k) for k in ("id", "reason", "status", "priority", "created_at")}
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
