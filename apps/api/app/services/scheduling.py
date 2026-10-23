from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.models.models import Appointment, Clinic, ClinicBusinessHours, DentalService, Provider, ScheduleException

VALID_APPOINTMENT_STATUSES = {"scheduled", "confirmed", "checked_in", "completed", "cancelled", "no_show"}
VALID_STATUS_TRANSITIONS = {
    "scheduled": {"confirmed", "cancelled"},
    "confirmed": {"checked_in", "cancelled", "completed"},
    "checked_in": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
    "no_show": set(),
}


class SchedulingConflictError(ValueError):
    pass


class InvalidStatusTransitionError(ValueError):
    pass


class ScheduleValidationError(ValueError):
    pass


def normalize_status(value: str | None, default: str = "scheduled") -> str:
    if value is None:
        return default
    status = str(value).strip().lower().replace(" ", "_")
    return status if status in VALID_APPOINTMENT_STATUSES else default


def normalize_datetime(value: datetime | str | None, clinic_tz: ZoneInfo) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value)
    else:
        raise ScheduleValidationError("Appointment time is required.")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=clinic_tz)
    return dt.astimezone(clinic_tz)


def resolve_provider_and_service(db: Session, clinic: Clinic, provider_id: str | None, service_id: str | None) -> tuple[Provider | None, DentalService | None]:
    provider = None
    if provider_id:
        provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
        if provider is None:
            raise ScheduleValidationError("Requested provider is not available for this clinic.")

    service = None
    if service_id:
        service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
        if service is None:
            raise ScheduleValidationError("Requested service is not available for this clinic.")

    if provider is None:
        provider = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True)).order_by(Provider.name.asc()).first()
    if service is None:
        service = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True)).order_by(DentalService.name.asc()).first()

    if provider is None:
        raise ScheduleValidationError("No active provider is configured for this clinic.")
    if service is None:
        raise ScheduleValidationError("No active service is configured for this clinic.")
    return provider, service


def get_provider_clinic_lock(db: Session, provider_id: str):
    if db.bind is None or getattr(db.bind.dialect, "name", "") != "postgresql":
        return
    db.execute(text("SELECT id FROM providers WHERE id = :provider_id FOR UPDATE"), {"provider_id": provider_id})


def get_clinic_day_schedule(db: Session, clinic: Clinic, target_date: datetime) -> list[ClinicBusinessHours]:
    clinic_tz = ZoneInfo(clinic.timezone or "UTC")
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=clinic_tz)
    day_start = target_date.astimezone(clinic_tz).replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    return (
        db.query(ClinicBusinessHours)
        .filter(
            ClinicBusinessHours.clinic_id == clinic.id,
            ClinicBusinessHours.weekday == day_start.weekday(),
        )
        .all()
    )


def get_clinic_day_exceptions(db: Session, clinic_id: str, provider_id: str | None, day_start: datetime, day_end: datetime) -> list[ScheduleException]:
    query = db.query(ScheduleException).filter(
        ScheduleException.clinic_id == clinic_id,
        ScheduleException.start_time < day_end,
        ScheduleException.end_time > day_start,
    )
    if provider_id:
        query = query.filter(or_(ScheduleException.provider_id == provider_id, ScheduleException.provider_id.is_(None)))
    return query.all()


def slot_overlaps_exception(slot_start: datetime, slot_end: datetime, exceptions: list[ScheduleException]) -> bool:
    return any(slot_start < exc.end_time and exc.start_time < slot_end for exc in exceptions)


def slot_has_existing_appointment(db: Session, clinic_id: str, provider_id: str, slot_start: datetime, slot_end: datetime, exclude_id: str | None = None) -> bool:
    query = db.query(Appointment).filter(
        Appointment.clinic_id == clinic_id,
        Appointment.provider_id == provider_id,
        Appointment.status != "cancelled",
        Appointment.start_time < slot_end,
        Appointment.end_time > slot_start,
    )
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.first() is not None


def available_slots_for_day(
    db: Session,
    clinic: Clinic,
    target_date: datetime,
    provider_id: str | None,
    service_id: str | None,
    time_preference: str | None = None,
) -> list[dict]:
    clinic_tz = ZoneInfo(clinic.timezone or "UTC")
    if target_date.tzinfo is None:
        target_day = target_date.replace(tzinfo=clinic_tz)
    else:
        target_day = target_date.astimezone(clinic_tz)
    day_start = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    business_hours = get_clinic_day_schedule(db, clinic, target_day)
    if not business_hours:
        return []

    if provider_id:
        provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
        if provider is None:
            raise ScheduleValidationError("Requested provider is not available for this clinic.")
    else:
        provider = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True)).order_by(Provider.name.asc()).first()

    service = None
    if service_id:
        service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
    if service is None:
        service = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True)).order_by(DentalService.name.asc()).first()
    if service is None:
        raise ScheduleValidationError("No active service is configured for this clinic.")

    duration_minutes = max(int(service.default_duration_minutes), 15)
    exceptions = get_clinic_day_exceptions(db, clinic.id, provider.id if provider else None, day_start, day_end)
    slots: list[dict] = []

    for business_window in business_hours:
        if business_window.is_closed:
            continue
        opening = datetime.combine(target_day.date(), datetime.strptime(business_window.opening_time, "%H:%M").time(), tzinfo=clinic_tz)
        closing = datetime.combine(target_day.date(), datetime.strptime(business_window.closing_time, "%H:%M").time(), tzinfo=clinic_tz)
        cursor = opening
        while cursor + timedelta(minutes=duration_minutes) <= closing:
            slot_end = cursor + timedelta(minutes=duration_minutes)
            if provider is not None and slot_has_existing_appointment(db, clinic.id, provider.id, cursor, slot_end):
                cursor = slot_end
                continue
            if slot_overlaps_exception(cursor, slot_end, exceptions):
                cursor = slot_end
                continue
            slots.append({"start_time": cursor, "end_time": slot_end, "provider_id": provider.id if provider else None})
            cursor = slot_end

    if time_preference:
        preference = time_preference.lower()
        if preference == "morning":
            slots = [slot for slot in slots if slot["start_time"].hour < 12]
        elif preference == "afternoon":
            slots = [slot for slot in slots if 12 <= slot["start_time"].hour < 17]
        elif preference == "evening":
            slots = [slot for slot in slots if slot["start_time"].hour >= 17]

    return slots[:12]


def validate_status_transition(current_status: str, next_status: str) -> None:
    current = normalize_status(current_status)
    next_value = normalize_status(next_status)
    allowed = VALID_STATUS_TRANSITIONS.get(current, set())
    if next_value not in allowed:
        raise InvalidStatusTransitionError(f"Status transition from '{current}' to '{next_value}' is not allowed.")


def ensure_no_overlap(db: Session, clinic_id: str, provider_id: str, start_time: datetime, end_time: datetime, exclude_id: str | None = None) -> None:
    if start_time >= end_time:
        raise ScheduleValidationError("Appointment end time must be after the start time.")
    if slot_has_existing_appointment(db, clinic_id, provider_id, start_time, end_time, exclude_id):
        raise SchedulingConflictError("Appointment overlaps with an existing provider schedule.")
