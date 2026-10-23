from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.core.authorization import require_permission, request_user
from app.db.session import get_db
from app.models.models import Appointment, AuditLog, Patient
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, AppointmentStatusUpdate, AvailabilityRequest
from app.services.scheduling import (available_slots_for_day, save_appointment, ScheduleValidationError,
    SchedulingConflictError, InvalidStatusTransitionError, stored_datetime)

router = APIRouter(prefix="/appointments", tags=["appointments"])


def scoped_appointment(db, appointment_id):
    _, clinic = get_default_tenant_and_clinic(db)
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.clinic_id == clinic.id).first()
    if appointment is None:
        raise HTTPException(404, "Appointment not found")
    return clinic, appointment


def serialize(a, clinic):
    return {"id": a.id, "appointment_id": a.id, "patient_id": a.patient_id, "provider_id": a.provider_id,
            "service_id": a.service_id, "status": a.status, "source": a.source,
            "start_time": stored_datetime(a.start_time).isoformat(), "end_time": stored_datetime(a.end_time).isoformat(),
            "timezone": clinic.timezone, "notes": a.notes}


def persist(db, clinic, patient, data, appointment=None):
    try:
        user = request_user.get()
        a = save_appointment(db, clinic, patient, data, actor_id=user.id if user else None, appointment=appointment)
        db.commit()
        return a
    except (SchedulingConflictError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(409, "Appointment overlaps with an existing provider schedule.") from exc
    except (ScheduleValidationError, InvalidStatusTransitionError) as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.post("/availability")
def get_availability(payload: AvailabilityRequest, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    if payload.clinic_id and payload.clinic_id != clinic.id:
        raise HTTPException(403, "Clinic context mismatch")
    try:
        slots = available_slots_for_day(db, clinic, datetime.fromisoformat(payload.preferred_date), payload.provider_id,
                                        payload.service_id, payload.time_preference)
    except (ValueError, ScheduleValidationError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"success": True, "status": "available" if slots else "unavailable", "timezone": clinic.timezone,
            "slots": [dict(s, slot_id=f"{s['provider_id']}:{s['start_time'].isoformat()}") for s in slots],
            "message": "Appointment slots found." if slots else "No appointment slots are available for this date."}


@router.get("")
def list_appointments(db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    items = db.query(Appointment).filter(Appointment.clinic_id == clinic.id).order_by(Appointment.start_time.desc()).limit(100).all()
    return {"items": [serialize(a, clinic) for a in items]}


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str, db: Session = Depends(get_db)):
    clinic, appointment = scoped_appointment(db, appointment_id)
    return serialize(appointment, clinic)


@router.get("/{appointment_id}/history")
def appointment_history(appointment_id: str, db: Session = Depends(get_db)):
    clinic, _ = scoped_appointment(db, appointment_id)
    items = db.query(AuditLog).filter(AuditLog.tenant_id == clinic.tenant_id, AuditLog.entity_type == "appointment",
        AuditLog.entity_id == appointment_id).order_by(AuditLog.timestamp).all()
    return {"items": [{"action": a.action, "actor_type": a.actor_type, "actor_id": a.actor_id,
        "timestamp": a.timestamp.isoformat(), "changes": json.loads(a.audit_metadata or "{}")} for a in items]}


@router.post("", status_code=201, dependencies=[Depends(require_permission("create_appointments"))])
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)):
    _, clinic = get_default_tenant_and_clinic(db)
    patient = db.query(Patient).filter(Patient.id == payload.patient_id, Patient.clinic_id == clinic.id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")
    a = persist(db, clinic, patient, payload.model_dump())
    return {"status": "created", "appointment_id": a.id}


@router.patch("/{appointment_id}", dependencies=[Depends(require_permission("update_appointments"))])
def update_appointment(appointment_id: str, payload: AppointmentUpdate, db: Session = Depends(get_db)):
    clinic, a = scoped_appointment(db, appointment_id)
    patient = db.get(Patient, a.patient_id)
    a = persist(db, clinic, patient, payload.model_dump(exclude_unset=True, exclude_none=True), a)
    return serialize(a, clinic)


@router.patch("/{appointment_id}/status", dependencies=[Depends(require_permission("update_appointments"))])
def update_appointment_status(appointment_id: str, payload: AppointmentStatusUpdate, db: Session = Depends(get_db)):
    clinic, a = scoped_appointment(db, appointment_id)
    a = persist(db, clinic, db.get(Patient, a.patient_id), payload.model_dump(exclude_none=True), a)
    return serialize(a, clinic)


@router.delete("/{appointment_id}", dependencies=[Depends(require_permission("update_appointments"))])
def delete_appointment(appointment_id: str, db: Session = Depends(get_db)):
    clinic, a = scoped_appointment(db, appointment_id)
    a = persist(db, clinic, db.get(Patient, a.patient_id), {"status": "cancelled"}, a)
    return dict(serialize(a, clinic), message="Appointment cancelled.")
