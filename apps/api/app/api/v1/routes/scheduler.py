from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import Appointment, Patient
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    AvailabilityRequest,
    AvailabilityResponse,
    Slot,
)
from app.services.scheduling import (
    InvalidStatusTransitionError,
    SchedulingConflictError,
    ScheduleValidationError,
    available_slots_for_day,
    ensure_no_overlap,
    get_provider_clinic_lock,
    normalize_status,
    resolve_provider_and_service,
    validate_status_transition,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/availability", response_model=AvailabilityResponse)
def get_availability(payload: AvailabilityRequest, db: Session = Depends(get_db)) -> AvailabilityResponse:
    preferred_date = datetime.fromisoformat(payload.preferred_date)
    _, clinic = get_default_tenant_and_clinic(db)

    try:
        slots = available_slots_for_day(
            db,
            clinic,
            preferred_date,
            provider_id=payload.provider_id,
            service_id=payload.service_id,
            time_preference=payload.time_preference,
        )
    except ScheduleValidationError as exc:
        return AvailabilityResponse(success=True, status="unavailable", slots=[], message=str(exc))

    items = [
        Slot(
            slot_id=f"slot-{slot['start_time'].strftime('%Y%m%d-%H%M')}",
            start_time=slot["start_time"],
            end_time=slot["end_time"],
            provider_id=slot.get("provider_id"),
        )
        for slot in slots
    ]

    return AvailabilityResponse(
        success=True,
        status="available" if items else "unavailable",
        slots=items,
        message="Appointment slots found." if items else "No appointment slots are available for this date.",
    )


@router.get("")
def list_appointments(db: Session = Depends(get_db)) -> dict[str, list]:
    _, clinic = get_default_tenant_and_clinic(db)
    appointments = db.query(Appointment).filter(Appointment.clinic_id == clinic.id).order_by(Appointment.start_time.desc()).limit(10).all()
    return {"items": [{"id": a.id, "status": a.status, "start_time": a.start_time.isoformat()} for a in appointments]}


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return {"id": appointment.id, "status": appointment.status}


@router.patch("/{appointment_id}")
def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
) -> dict:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if payload.status is not None:
        try:
            validate_status_transition(appointment.status, payload.status)
        except InvalidStatusTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    provider_id = payload.provider_id or appointment.provider_id
    start_time = payload.start_time or appointment.start_time
    end_time = payload.end_time or appointment.end_time

    if start_time >= end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment end time must be after the start time.")

    if payload.provider_id is not None or payload.start_time is not None or payload.end_time is not None:
        try:
            get_provider_clinic_lock(db, provider_id)
            ensure_no_overlap(db, appointment.clinic_id, provider_id, start_time, end_time, exclude_id=appointment.id)
        except (ScheduleValidationError, SchedulingConflictError) as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT if isinstance(exc, SchedulingConflictError) else status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if payload.provider_id is not None:
        appointment.provider_id = payload.provider_id
    if payload.service_id is not None:
        appointment.service_id = payload.service_id
    if payload.start_time is not None:
        appointment.start_time = payload.start_time
    if payload.end_time is not None:
        appointment.end_time = payload.end_time
    if payload.notes is not None:
        appointment.notes = payload.notes
    if payload.status is not None:
        appointment.status = normalize_status(payload.status)

    db.commit()
    db.refresh(appointment)
    return {
        "id": appointment.id,
        "status": appointment.status,
        "start_time": appointment.start_time.isoformat(),
        "end_time": appointment.end_time.isoformat(),
        "notes": appointment.notes,
    }


@router.patch("/{appointment_id}/status")
def update_appointment_status(
    appointment_id: str,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
) -> dict:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    try:
        validate_status_transition(appointment.status, payload.status)
    except InvalidStatusTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    appointment.status = normalize_status(payload.status)
    if payload.notes is not None:
        appointment.notes = payload.notes
    db.commit()
    db.refresh(appointment)
    return {"id": appointment.id, "status": appointment.status, "notes": appointment.notes}


@router.delete("/{appointment_id}")
def delete_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
) -> dict:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if appointment.status == "cancelled":
        return {"id": appointment.id, "status": appointment.status, "notes": appointment.notes, "message": "Appointment already cancelled."}

    appointment.status = "cancelled"
    if appointment.notes is None:
        appointment.notes = "Cancelled by front desk."
    db.commit()
    db.refresh(appointment)
    return {"id": appointment.id, "status": appointment.status, "notes": appointment.notes, "message": "Appointment cancelled."}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    _, clinic = get_default_tenant_and_clinic(db)
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    try:
        provider, service = resolve_provider_and_service(db, clinic, payload.provider_id, payload.service_id)
        get_provider_clinic_lock(db, provider.id)
        ensure_no_overlap(db, clinic.id, provider.id, payload.start_time, payload.end_time)
    except (ScheduleValidationError, SchedulingConflictError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if isinstance(exc, SchedulingConflictError) else status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    appointment = Appointment(
        tenant_id=patient.tenant_id,
        clinic_id=clinic.id,
        patient_id=patient.id,
        provider_id=provider.id,
        service_id=service.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=normalize_status(payload.status),
        source=payload.source,
        notes=payload.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return {"status": "created", "appointment_id": appointment.id}
