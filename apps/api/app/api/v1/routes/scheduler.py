from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.api.v1.routes.staff import require_permission
from app.db.session import get_db
from app.models.models import Appointment, ClinicBusinessHours, DentalService, Patient, Provider
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    AvailabilityRequest,
    AvailabilityResponse,
    Slot,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/availability", response_model=AvailabilityResponse)
def get_availability(payload: AvailabilityRequest, db: Session = Depends(get_db)) -> AvailabilityResponse:
    preferred_date = datetime.fromisoformat(payload.preferred_date)
    _, clinic = get_default_tenant_and_clinic(db)
    existing = db.query(Appointment).filter(
        Appointment.clinic_id == clinic.id,
        Appointment.start_time >= preferred_date.replace(hour=0, minute=0, second=0, microsecond=0),
        Appointment.start_time < preferred_date.replace(hour=23, minute=59, second=59, microsecond=999999),
    ).all()

    business_hours = db.query(ClinicBusinessHours).filter(
        ClinicBusinessHours.clinic_id == clinic.id,
        ClinicBusinessHours.weekday == preferred_date.weekday(),
    ).first()

    if business_hours is None or business_hours.is_closed:
        return AvailabilityResponse(
            success=True,
            status="unavailable",
            slots=[],
            message="The clinic is closed on this date.",
        )

    start = preferred_date.replace(hour=int(business_hours.opening_time.split(":")[0]), minute=int(business_hours.opening_time.split(":")[1]), second=0, microsecond=0)
    end = preferred_date.replace(hour=int(business_hours.closing_time.split(":")[0]), minute=int(business_hours.closing_time.split(":")[1]), second=0, microsecond=0)

    preferred = (payload.time_preference or "morning").lower()
    time_windows: list[tuple[datetime, datetime]] = []
    current = start
    while current + timedelta(minutes=30) <= end:
        next_time = current + timedelta(minutes=30)
        occupied = any(current < appt.end_time and appt.start_time < next_time for appt in existing)
        if not occupied:
            time_windows.append((current, next_time))
        current = next_time

    if preferred == "morning":
        time_windows = [window for window in time_windows if window[0].hour < 12]
    elif preferred == "afternoon":
        time_windows = [window for window in time_windows if window[0].hour >= 12]
    elif preferred == "evening":
        time_windows = [window for window in time_windows if window[0].hour >= 17]

    slots = [
        Slot(
            slot_id=f"slot-{start_value.strftime('%Y%m%d-%H%M')}",
            start_time=start_value,
            end_time=end_value,
            provider_id=payload.provider_id or "provider-demo",
        )
        for start_value, end_value in time_windows[:8]
    ]

    return AvailabilityResponse(
        success=True,
        status="available" if slots else "unavailable",
        slots=slots,
        message="Appointment slots found." if slots else "No appointment slots are available for this date.",
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
        valid_statuses = {"scheduled", "confirmed", "checked_in", "completed", "cancelled"}
        normalized_status = payload.status.lower()
        if normalized_status not in valid_statuses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid appointment status.")
        appointment.status = normalized_status

    if appointment.start_time >= appointment.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment end time must be after the start time.")

    overlap = db.query(Appointment).filter(
        Appointment.clinic_id == appointment.clinic_id,
        Appointment.provider_id == appointment.provider_id,
        Appointment.id != appointment_id,
        Appointment.status != "cancelled",
        Appointment.start_time < appointment.end_time,
        Appointment.end_time > appointment.start_time,
    ).first()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment overlaps with an existing provider schedule.",
        )

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

    valid_statuses = {"scheduled", "confirmed", "checked_in", "completed", "cancelled"}
    normalized_status = payload.status.lower()
    if normalized_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid appointment status.")

    appointment.status = normalized_status
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

    provider_id = payload.provider_id or db.query(Provider).filter(Provider.clinic_id == clinic.id).first().id
    service_id = payload.service_id or db.query(DentalService).filter(DentalService.clinic_id == clinic.id).first().id

    overlap = db.query(Appointment).filter(
        Appointment.clinic_id == clinic.id,
        Appointment.provider_id == provider_id,
        Appointment.status != "cancelled",
        Appointment.start_time < payload.end_time,
        Appointment.end_time > payload.start_time,
    ).first()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment overlaps with an existing provider schedule.",
        )

    appointment = Appointment(
        tenant_id=patient.tenant_id,
        clinic_id=clinic.id,
        patient_id=patient.id,
        provider_id=provider_id,
        service_id=service_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=payload.status,
        source=payload.source,
        notes=payload.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return {"status": "created", "appointment_id": appointment.id}
