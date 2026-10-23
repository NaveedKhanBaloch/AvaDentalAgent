from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import Appointment, CallLog, FollowUp, Patient, AuditLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo(clinic.timezone or "UTC")).replace(hour=0, minute=0, second=0, microsecond=0)
    appointments = db.query(Appointment).filter(Appointment.clinic_id == clinic.id)
    calls = db.query(CallLog).filter(CallLog.clinic_id == clinic.id)
    return {
        "appointments_today": appointments.filter(Appointment.start_time >= today.astimezone(timezone.utc),
            Appointment.start_time < (today + timedelta(days=1)).astimezone(timezone.utc)).count(),
        "upcoming": appointments.filter(Appointment.start_time >= now, Appointment.start_time <= now + timedelta(days=7),
            Appointment.status.in_(["scheduled", "confirmed"])).count(),
        "pending_confirmations": appointments.filter(Appointment.status == "scheduled").count(),
        "cancelled": appointments.filter(Appointment.status == "cancelled").count(),
        "ai_bookings": appointments.filter(Appointment.source == "retell").count(),
        "rescheduled": db.query(AuditLog).filter(AuditLog.tenant_id == clinic.tenant_id,
            AuditLog.action == "appointment.reschedule", AuditLog.entity_id.in_(appointments.with_entities(Appointment.id))).count(),
        "new_patients": db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.created_at >= now - timedelta(days=30)).count(),
        "calls_handled": calls.count(),
        "missed_calls": calls.filter(CallLog.status == "missed").count(),
        "unresolved_calls": calls.filter(CallLog.outcome == "unresolved").count(),
        "follow_up_requests": db.query(FollowUp).filter(FollowUp.clinic_id == clinic.id, FollowUp.status.in_(["pending", "in_progress"])).count(),
    }

@router.get("/analytics")
def dashboard_analytics(db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    today = datetime.now(ZoneInfo(clinic.timezone or "UTC")).replace(hour=0, minute=0, second=0, microsecond=0)
    trends = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        trends.append(db.query(Appointment).filter(Appointment.clinic_id == clinic.id,
            Appointment.start_time >= day.astimezone(timezone.utc),
            Appointment.start_time < (day + timedelta(days=1)).astimezone(timezone.utc)).count())
    outcomes = dict(db.query(CallLog.outcome, func.count(CallLog.id)).filter(CallLog.clinic_id == clinic.id).group_by(CallLog.outcome).all())
    return {"appointment_trends": trends, "call_outcomes": {key: outcomes.get(key, 0) for key in ("booked", "missed", "follow_up", "unresolved")}}
