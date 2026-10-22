from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import Appointment, ClinicBusinessHours, DentalService, Patient, Provider
from app.schemas.appointment import AppointmentCreate, AvailabilityRequest, AvailabilityResponse, Slot

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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    _, clinic = get_default_tenant_and_clinic(db)
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    provider_id = payload.provider_id or db.query(Provider).filter(Provider.clinic_id == clinic.id).first().id
    service_id = payload.service_id or db.query(DentalService).filter(DentalService.clinic_id == clinic.id).first().id

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
