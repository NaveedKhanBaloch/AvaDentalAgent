from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, StrictBool
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.authorization import (
    capabilities,
    get_user_default_clinic,
    request_user,
    require_permission,
)
from app.db.session import get_db
from app.models.models import FollowUp, Patient, Recall, RecallRule, ReminderPreparation
from app.schemas.operations import FollowUpCreate, FollowUpUpdate, RecallCreate, RecallUpdate
from app.services.followups import save_operation, serialize
from app.services.patient_operations import page_query, scoped

router = APIRouter(prefix="/operations", tags=["patient operations"])


def listing(
    db,
    kind,
    search,
    status,
    priority,
    assigned_user_id,
    due_from,
    due_to,
    overdue,
    patient_id,
    page,
    page_size,
):
    _, clinic = get_user_default_clinic(db)
    model = FollowUp if kind == "followup" else Recall
    due = model.due_at if kind == "followup" else model.due_date
    query = (
        db.query(model)
        .outerjoin(Patient, Patient.id == model.patient_id)
        .filter(model.clinic_id == clinic.id)
    )
    if search:
        term = "%" + search + "%"
        query = query.filter(
            or_(
                model.reason.ilike(term),
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
            )
        )
    if status:
        query = query.filter(model.status == status)
    if priority and kind == "followup":
        query = query.filter(model.priority == priority)
    if assigned_user_id:
        query = query.filter(model.assigned_user_id == assigned_user_id)
    if patient_id:
        query = query.filter(model.patient_id == patient_id)
    if due_from:
        query = query.filter(due >= due_from)
    if due_to:
        query = query.filter(due <= due_to)
    if overdue:
        cutoff = (
            datetime.now(timezone.utc)
            if kind == "followup"
            else datetime.now(ZoneInfo(clinic.timezone or "UTC")).date()
        )
        query = query.filter(due < cutoff, ~model.status.in_(["completed", "cancelled"]))
    rows, total = page_query(query.order_by(due.asc().nullslast(), model.id), page, page_size)
    patients = {
        p.id: p
        for p in db.query(Patient).filter(
            Patient.clinic_id == clinic.id,
            Patient.id.in_([r.patient_id for r in rows if r.patient_id]),
        )
    }
    return {
        "items": [
            dict(
                serialize(r),
                patient_name=(
                    (patients[r.patient_id].first_name + " " + patients[r.patient_id].last_name)
                    if r.patient_id in patients
                    else None
                ),
            )
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/follow-ups", dependencies=[Depends(require_permission("followup_read"))])
def list_followups(
    search: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assigned_user_id: str | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    overdue: bool = False,
    patient_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return listing(
        db,
        "followup",
        search,
        status,
        priority,
        assigned_user_id,
        due_from,
        due_to,
        overdue,
        patient_id,
        page,
        page_size,
    )


@router.get("/recalls", dependencies=[Depends(require_permission("recall_read"))])
def list_recalls(
    search: str | None = None,
    status: str | None = None,
    assigned_user_id: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    overdue: bool = False,
    patient_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return listing(
        db,
        "recall",
        search,
        status,
        None,
        assigned_user_id,
        due_from,
        due_to,
        overdue,
        patient_id,
        page,
        page_size,
    )


@router.post(
    "/follow-ups", status_code=201, dependencies=[Depends(require_permission("followup_write"))]
)
def create_followup(payload: FollowUpCreate, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    r = save_operation(db, clinic, payload.model_dump())
    db.commit()
    return serialize(r)


@router.get("/follow-ups/{record_id}", dependencies=[Depends(require_permission("followup_read"))])
def get_followup(record_id: str, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    return serialize(scoped(db, FollowUp, record_id, clinic))


@router.patch(
    "/follow-ups/{record_id}", dependencies=[Depends(require_permission("followup_write"))]
)
def update_followup(record_id: str, payload: FollowUpUpdate, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    r = save_operation(
        db, clinic, payload.model_dump(), record=scoped(db, FollowUp, record_id, clinic, True)
    )
    db.commit()
    return serialize(r)


@router.post(
    "/recalls", status_code=201, dependencies=[Depends(require_permission("recall_write"))]
)
def create_recall(payload: RecallCreate, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    r = save_operation(db, clinic, payload.model_dump(), "recall")
    db.commit()
    return serialize(r)


@router.get("/recalls/{record_id}", dependencies=[Depends(require_permission("recall_read"))])
def get_recall(record_id: str, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    return serialize(scoped(db, Recall, record_id, clinic))


@router.patch("/recalls/{record_id}", dependencies=[Depends(require_permission("recall_write"))])
def update_recall(record_id: str, payload: RecallUpdate, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    r = save_operation(
        db, clinic, payload.model_dump(), "recall", scoped(db, Recall, record_id, clinic, True)
    )
    db.commit()
    return serialize(r)


@router.get("/recall-rules", dependencies=[Depends(require_permission("recall_read"))])
def list_rules(db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    return {
        "items": [
            serialize(r)
            for r in db.query(RecallRule).filter_by(clinic_id=clinic.id).order_by(RecallRule.name)
        ]
    }


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    interval_days: int = Field(ge=1, le=3650)
    clinically_approved: StrictBool


@router.post(
    "/recall-rules", status_code=201, dependencies=[Depends(require_permission("manage_schedule"))]
)
def add_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    user = request_user.get()
    if not user or not payload.clinically_approved:
        raise HTTPException(422, "Authenticated clinical approval attribution is required")
    if db.query(RecallRule).filter_by(clinic_id=clinic.id, name=payload.name).first():
        raise HTTPException(409, "Recall rule already exists")
    rule = RecallRule(
        clinic_id=clinic.id,
        name=payload.name,
        interval_days=payload.interval_days,
        approved_by=user.id,
    )
    db.add(rule)
    db.flush()
    from app.services.patient_operations import event

    event(db, clinic, "recall_rule.approved", rule)
    db.commit()
    return serialize(rule)


@router.post("/reminders/prepare", dependencies=[Depends(require_permission("operations_report"))])
def prepare(db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    from app.services.reminders import prepare_reminders

    return prepare_reminders(db, clinic)


@router.get("/reminders", dependencies=[Depends(require_permission("operations_report"))])
def reminders(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _, clinic = get_user_default_clinic(db)
    rows, total = page_query(
        db.query(ReminderPreparation)
        .filter_by(clinic_id=clinic.id)
        .order_by(ReminderPreparation.created_at.desc()),
        page,
        page_size,
    )
    return {
        "items": [serialize(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/metrics", dependencies=[Depends(require_permission("operations_report"))])
def metrics(db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo(clinic.timezone or "UTC"))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    follow = db.query(FollowUp).filter(FollowUp.clinic_id == clinic.id)
    opened = follow.filter(FollowUp.status.in_(["pending", "in_progress"]))
    result = {
        "active_patients": db.query(Patient)
        .filter_by(clinic_id=clinic.id, status="active")
        .count(),
        "new_patients_30d": db.query(Patient)
        .filter(Patient.clinic_id == clinic.id, Patient.created_at >= now - timedelta(days=30))
        .count(),
        "pending_followups": opened.count(),
        "overdue_followups": opened.filter(FollowUp.due_at < now).count(),
        "followups_due_today": opened.filter(
            FollowUp.due_at >= start.astimezone(timezone.utc),
            FollowUp.due_at < end.astimezone(timezone.utc),
        ).count(),
        "completed_followups": follow.filter(FollowUp.status == "completed").count(),
        "recalls_due": db.query(Recall)
        .filter(
            Recall.clinic_id == clinic.id,
            Recall.due_date <= local.date(),
            ~Recall.status.in_(["completed", "cancelled"]),
        )
        .count(),
        "timezone": clinic.timezone,
    }
    if "estimate_read" in capabilities(db):
        from app.models.models import TreatmentEstimate

        for state in ["draft", "sent", "accepted", "declined"]:
            result["estimates_" + state] = (
                db.query(TreatmentEstimate).filter_by(clinic_id=clinic.id, status=state).count()
            )
    return result
