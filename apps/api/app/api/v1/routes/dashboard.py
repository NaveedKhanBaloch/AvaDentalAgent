from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import Appointment, CallLog, FollowUp, Patient

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    now = datetime.now()
    today = date.today()
    appointments = db.query(Appointment).filter(Appointment.clinic_id == clinic.id).all()

    summary = {
        "appointments_today": sum(1 for appt in appointments if appt.start_time.date() == today),
        "upcoming": sum(1 for appt in appointments if appt.start_time >= now and appt.start_time <= now + timedelta(days=7)),
        "pending_confirmations": sum(1 for appt in appointments if appt.status in {"scheduled", "pending"}),
        "cancelled": sum(1 for appt in appointments if appt.status == "cancelled"),
        "new_patients": db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.created_at >= now - timedelta(days=30)).count(),
        "calls_handled": db.query(CallLog).filter(CallLog.clinic_id == clinic.id).count(),
        "missed_calls": db.query(CallLog).filter(CallLog.clinic_id == clinic.id, CallLog.status == "missed").count(),
        "follow_up_requests": db.query(FollowUp).filter(FollowUp.clinic_id == clinic.id, FollowUp.status.in_(["pending", "in_progress"])).count(),
    }
    return summary


@router.get("/analytics")
def dashboard_analytics(db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    appointments = db.query(Appointment).filter(Appointment.clinic_id == clinic.id).all()
    trends = []
    for offset in range(6, -1, -1):
        day = date.today() - timedelta(days=offset)
        count = sum(1 for appt in appointments if appt.start_time.date() == day)
        trends.append(count)

    call_outcomes = {"booked": 0, "missed": 0, "follow_up": 0}
    for outcome in ("booked", "missed", "follow_up"):
        call_outcomes[outcome] = db.query(CallLog).filter(CallLog.clinic_id == clinic.id, CallLog.outcome == outcome).count()

    return {
        "appointment_trends": trends,
        "call_outcomes": call_outcomes,
    }
