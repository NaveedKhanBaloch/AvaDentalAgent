from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import Appointment, DentalService, Patient, Provider

router = APIRouter(prefix="/integrations/retell", tags=["retell"])


@router.post("/functions/check-availability")
def retell_check_availability() -> dict:
    return {"success": True, "status": "available", "slots": [], "message": "Availability checked."}


@router.post("/functions/create-appointment")
def retell_create_appointment() -> dict:
    return {"success": True, "status": "confirmed", "appointment_id": "retell-demo-appointment", "message": "Appointment created."}


@router.post("/functions/verify-patient")
def retell_verify_patient() -> dict:
    return {"success": True, "status": "verified", "patient_id": "demo-patient", "message": "Patient verified."}


@router.post("/functions/get-appointment")
def retell_get_appointment() -> dict:
    return {"success": True, "status": "found", "appointment": {"id": "demo-appointment"}}


@router.post("/functions/reschedule-appointment")
def retell_reschedule_appointment() -> dict:
    return {"success": True, "status": "rescheduled", "appointment_id": "demo-appointment"}


@router.post("/functions/cancel-appointment")
def retell_cancel_appointment() -> dict:
    return {"success": True, "status": "cancelled", "appointment_id": "demo-appointment"}


@router.post("/functions/create-followup")
def retell_create_followup() -> dict:
    return {"success": True, "status": "created", "followup_id": "demo-followup"}


@router.post("/webhooks")
def retell_webhook(payload: dict, db: Session = Depends(get_db)) -> dict:
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Retell webhook payload is required.")

    patient_payload = payload.get("patient") or {}
    tenant, clinic = get_default_tenant_and_clinic(db)

    phone = str(patient_payload.get("phone") or payload.get("phone") or "").strip()
    email = str(patient_payload.get("email") or payload.get("email") or "").strip()
    first_name = str(patient_payload.get("first_name") or payload.get("first_name") or "New").strip()
    last_name = str(patient_payload.get("last_name") or payload.get("last_name") or "Patient").strip()

    patient = None
    if email:
        patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.email == email).first()
    if patient is None and phone:
        patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.phone == phone).first()
    if patient is None:
        patient = Patient(
            tenant_id=tenant.id,
            clinic_id=clinic.id,
            first_name=first_name or "New",
            last_name=last_name or "Patient",
            phone=phone or None,
            email=email or None,
            preferred_contact_method="phone",
            notes=payload.get("notes") or "Created from Retell webhook.",
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    provider_id = payload.get("provider_id")
    provider = None
    if provider_id:
        provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
    if provider is None:
        provider = db.query(Provider).filter(Provider.clinic_id == clinic.id).first()
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No provider is configured for this clinic.")

    service_id = payload.get("service_id")
    service = None
    if service_id:
        service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
    if service is None:
        service = db.query(DentalService).filter(DentalService.clinic_id == clinic.id).first()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No service is configured for this clinic.")

    start_time_value = payload.get("start_time")
    end_time_value = payload.get("end_time")
    if isinstance(start_time_value, str):
        start_time = datetime.fromisoformat(start_time_value)
    else:
        start_time = datetime.utcnow() + timedelta(hours=1)
    if isinstance(end_time_value, str):
        end_time = datetime.fromisoformat(end_time_value)
    else:
        end_time = start_time + timedelta(minutes=service.default_duration_minutes)

    overlap = db.query(Appointment).filter(
        Appointment.clinic_id == clinic.id,
        Appointment.provider_id == provider.id,
        Appointment.status != "cancelled",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    ).first()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retell booking overlaps with an existing provider schedule.",
        )

    appointment = Appointment(
        tenant_id=tenant.id,
        clinic_id=clinic.id,
        patient_id=patient.id,
        provider_id=provider.id,
        service_id=service.id,
        start_time=start_time,
        end_time=end_time,
        status=str(payload.get("status") or "scheduled").lower(),
        source=str(payload.get("source") or "retell").lower(),
        notes=str(payload.get("notes") or "Created by Retell AI receptionist."),
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return {"status": "accepted", "appointment_id": appointment.id, "message": "Retell booking captured into the clinic schedule."}
