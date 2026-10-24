from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.core.audit import write_audit_event
from app.models.models import (Appointment, Clinic, ClinicBusinessHours, DentalService, Provider,
                               ProviderService, ProviderWorkingHours, ScheduleException)

VALID_APPOINTMENT_STATUSES = {"scheduled", "confirmed", "checked_in", "completed", "cancelled", "no_show"}
VALID_STATUS_TRANSITIONS = {
    "scheduled": {"confirmed", "cancelled", "no_show"},
    "confirmed": {"checked_in", "cancelled", "completed", "no_show"},
    "checked_in": {"completed", "cancelled"},
    "completed": set(), "cancelled": set(), "no_show": set(),
}
TERMINAL = {"completed", "cancelled", "no_show"}
UTC = timezone.utc

class SchedulingConflictError(ValueError):
    pass

class InvalidStatusTransitionError(ValueError):
    pass

class ScheduleValidationError(ValueError):
    pass


def normalize_status(value: str | None, default: str = "scheduled") -> str:
    status = str(value if value is not None else default).strip().lower().replace(" ", "_")
    if status not in VALID_APPOINTMENT_STATUSES:
        raise InvalidStatusTransitionError("Unknown appointment status.")
    return status


def normalize_datetime(value: datetime | str | None, clinic_tz: ZoneInfo) -> datetime:
    try:
        dt = datetime.fromisoformat(value) if isinstance(value, str) else value
        if not isinstance(dt, datetime):
            raise ValueError()
        if dt.tzinfo is None:
            candidates = {dt.replace(tzinfo=clinic_tz, fold=f).astimezone(UTC) for f in (0, 1)
                          if dt.replace(tzinfo=clinic_tz, fold=f).astimezone(UTC).astimezone(clinic_tz).replace(tzinfo=None) == dt}
            if len(candidates) != 1:
                raise ScheduleValidationError("Ambiguous or nonexistent local time; supply a valid UTC offset.")
            return candidates.pop().astimezone(clinic_tz)
        return dt.astimezone(clinic_tz)
    except (ValueError, TypeError) as exc:
        raise ScheduleValidationError("A valid appointment timestamp is required.") from exc


def stored_datetime(value: datetime) -> datetime:
    # SQLite test adapter drops tzinfo; persisted values are always UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def resolve_provider_and_service(db: Session, clinic: Clinic, provider_id: str | None, service_id: str | None):
    providers = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True))
    services = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True))
    provider = providers.filter(Provider.id == provider_id).first() if provider_id else providers.order_by(Provider.name).first()
    service = services.filter(DentalService.id == service_id).first() if service_id else services.order_by(DentalService.name).first()
    if provider is None or service is None:
        raise ScheduleValidationError("Requested active provider or service is unavailable for this clinic.")
    mappings = db.query(ProviderService).filter(ProviderService.provider_id == provider.id).all()
    if mappings and service.id not in {item.service_id for item in mappings}:
        raise ScheduleValidationError("Provider does not offer the requested service.")
    if service.default_duration_minutes <= 0:
        raise ScheduleValidationError("Service duration must be positive.")
    return provider, service


def get_provider_clinic_lock(db: Session, provider_id: str):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT id FROM providers WHERE id = :provider_id FOR UPDATE"), {"provider_id": provider_id})


def get_clinic_day_schedule(db: Session, clinic: Clinic, target_date: datetime):
    return db.query(ClinicBusinessHours).filter(ClinicBusinessHours.clinic_id == clinic.id,
                                               ClinicBusinessHours.weekday == target_date.weekday()).all()


def get_clinic_day_exceptions(db: Session, clinic_id: str, provider_id: str | None, day_start: datetime, day_end: datetime):
    return db.query(ScheduleException).filter(
        ScheduleException.clinic_id == clinic_id,
        or_(ScheduleException.provider_id == provider_id, ScheduleException.provider_id.is_(None)),
        ScheduleException.start_time < day_end.astimezone(UTC),
        ScheduleException.end_time > day_start.astimezone(UTC)).all()


def slot_overlaps_exception(slot_start, slot_end, exceptions):
    return any(slot_start.astimezone(UTC) < stored_datetime(e.end_time) and
               stored_datetime(e.start_time) < slot_end.astimezone(UTC) for e in exceptions)


def slot_has_existing_appointment(db, clinic_id, provider_id, slot_start, slot_end, exclude_id=None):
    query = db.query(Appointment).filter(Appointment.clinic_id == clinic_id, Appointment.provider_id == provider_id,
        Appointment.status != "cancelled", Appointment.start_time < slot_end.astimezone(UTC),
        Appointment.end_time > slot_start.astimezone(UTC))
    if exclude_id:
        query = query.filter(Appointment.id != exclude_id)
    return query.first() is not None


def windows_for_day(db, clinic, provider, day):
    tz = ZoneInfo(clinic.timezone or "UTC")
    clinic_hours = get_clinic_day_schedule(db, clinic, day)
    if any(h.is_closed for h in clinic_hours):
        return []
    configured = db.query(ProviderWorkingHours).filter(ProviderWorkingHours.provider_id == provider.id).all()
    provider_hours = [h for h in configured if h.weekday == day.weekday()]
    windows = []
    def bounds(h):
        opening = normalize_datetime(f"{day.date()}T{h.opening_time}", tz).astimezone(UTC)
        closing = normalize_datetime(f"{day.date()}T{h.closing_time}", tz).astimezone(UTC)
        if closing <= opening:
            closing = normalize_datetime(f"{(day + timedelta(days=1)).date()}T{h.closing_time}", tz).astimezone(UTC)
        return opening, closing
    for h in clinic_hours:
        try:
            start, end = bounds(h)
            if not configured:
                windows.append((start, end))
            for p in provider_hours:
                ps, pe = bounds(p)
                if max(start, ps) < min(end, pe):
                    windows.append((max(start, ps), min(end, pe)))
        except ScheduleValidationError:
            # Fail closed when configured boundary itself is ambiguous/nonexistent.
            continue
    return windows


def validate_slot(db, clinic, provider, service, start_time, end_time, exclude_id=None):
    tz = ZoneInfo(clinic.timezone or "UTC")
    start = normalize_datetime(start_time, tz).astimezone(UTC)
    end = normalize_datetime(end_time, tz).astimezone(UTC)
    if start >= end:
        raise ScheduleValidationError("Appointment end time must be after the start time.")
    if end - start < timedelta(minutes=service.default_duration_minutes):
        raise ScheduleValidationError("Appointment is shorter than the service duration.")
    day = start.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    windows = windows_for_day(db, clinic, provider, day - timedelta(days=1)) + windows_for_day(db, clinic, provider, day)
    if not any(ws <= start and end <= we for ws, we in windows):
        raise ScheduleValidationError("Appointment is outside clinic or provider working hours.")
    exceptions = get_clinic_day_exceptions(db, clinic.id, provider.id, start, end)
    if slot_overlaps_exception(start, end, exceptions):
        raise ScheduleValidationError("Provider or clinic is unavailable during this interval.")
    ensure_no_overlap(db, clinic.id, provider.id, start, end, exclude_id)
    return start, end


def available_slots_for_day(db, clinic, target_date, provider_id, service_id, time_preference=None):
    tz = ZoneInfo(clinic.timezone or "UTC")
    day = normalize_datetime(target_date, tz).replace(hour=0, minute=0, second=0, microsecond=0)
    providers = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True))
    if provider_id:
        providers = providers.filter(Provider.id == provider_id)
    candidates = providers.order_by(Provider.name).all()
    if provider_id and not candidates:
        raise ScheduleValidationError("Requested provider is unavailable.")
    slots = []
    for provider in candidates:
        try:
            _, service = resolve_provider_and_service(db, clinic, provider.id, service_id)
        except ScheduleValidationError:
            if provider_id:
                raise
            continue
        duration = timedelta(minutes=service.default_duration_minutes)
        day_end = day + timedelta(days=1)
        exceptions = get_clinic_day_exceptions(db, clinic.id, provider.id, day, day_end + timedelta(days=1))
        occupied = db.query(Appointment).filter(Appointment.clinic_id == clinic.id,
            Appointment.provider_id == provider.id, Appointment.status != "cancelled",
            Appointment.start_time < day_end.astimezone(UTC) + timedelta(days=1),
            Appointment.end_time > day.astimezone(UTC)).all()
        windows = windows_for_day(db, clinic, provider, day - timedelta(days=1)) + windows_for_day(db, clinic, provider, day)
        seen = set()
        for opening, closing in windows:
            cursor = opening
            while cursor + duration <= closing:
                end = cursor + duration
                local = cursor.astimezone(tz)
                matches = not time_preference or (time_preference == "morning" and local.hour < 12) or (time_preference == "afternoon" and 12 <= local.hour < 17) or (time_preference == "evening" and local.hour >= 17)
                occupied_slot = any(cursor < stored_datetime(a.end_time) and stored_datetime(a.start_time) < end for a in occupied)
                if local.date() == day.date() and cursor not in seen and matches and not occupied_slot and not slot_overlaps_exception(cursor, end, exceptions):
                    slots.append({"start_time": local, "end_time": end.astimezone(tz), "provider_id": provider.id, "timezone": str(tz)})
                    seen.add(cursor)
                cursor = end
    return sorted(slots, key=lambda s: (s["start_time"].astimezone(UTC), s["provider_id"]))[:12]


def validate_status_transition(current_status, next_status):
    current, target = normalize_status(current_status), normalize_status(next_status)
    if current == target:
        return
    if target not in VALID_STATUS_TRANSITIONS[current]:
        raise InvalidStatusTransitionError(f"Status transition from '{current}' to '{target}' is not allowed.")


def ensure_no_overlap(db, clinic_id, provider_id, start_time, end_time, exclude_id=None):
    if start_time >= end_time:
        raise ScheduleValidationError("Appointment end time must be after the start time.")
    if slot_has_existing_appointment(db, clinic_id, provider_id, start_time, end_time, exclude_id):
        raise SchedulingConflictError("Appointment overlaps with an existing provider schedule.")


def save_appointment(db, clinic, patient, data, actor_type="user", actor_id=None, appointment=None):
    # Caller owns the transaction; audit and appointment commit atomically.
    if appointment is None and patient.status != "active":
        raise ScheduleValidationError("Archived patients must be restored before booking.")
    if patient.clinic_id != clinic.id or patient.tenant_id != clinic.tenant_id:
        raise ScheduleValidationError("Patient is unavailable for this clinic.")
    existing = appointment is not None
    before = None
    if existing:
        # Provider locks serialize writes; appointment row locks serialize transitions.
        db.refresh(appointment, with_for_update=True)
        before = {"status": appointment.status, "start_time": appointment.start_time.isoformat(),
                  "end_time": appointment.end_time.isoformat(), "provider_id": appointment.provider_id}
        target = normalize_status(data.get("status"), appointment.status)
        validate_status_transition(appointment.status, target)
        moving = any(k in data for k in ("provider_id", "service_id", "start_time", "end_time"))
        if moving and appointment.status in TERMINAL:
            raise InvalidStatusTransitionError("Terminal appointments cannot be rescheduled.")
    else:
        target = normalize_status(data.get("status"))
        if target not in {"scheduled", "confirmed"}:
            raise InvalidStatusTransitionError("New appointments must be scheduled or confirmed.")
        moving = True
    provider_id = data.get("provider_id") or (appointment.provider_id if existing else None)
    service_id = data.get("service_id") or (appointment.service_id if existing else None)
    if moving:
        provider, service = resolve_provider_and_service(db, clinic, provider_id, service_id)
    else:
        provider, service = db.get(Provider, provider_id), db.get(DentalService, service_id)
    if provider is not None:
        get_provider_clinic_lock(db, provider.id)
    if moving:
        start_value = data.get("start_time") or (stored_datetime(appointment.start_time) if existing else None)
        end_value = data.get("end_time") or (stored_datetime(appointment.end_time) if existing else None)
        start, end = validate_slot(db, clinic, provider, service, start_value, end_value, appointment.id if existing else None)
    if not existing:
        appointment = Appointment(tenant_id=clinic.tenant_id, clinic_id=clinic.id, patient_id=patient.id,
                                  provider_id=provider.id, service_id=service.id, source=data.get("source", "dashboard"))
        db.add(appointment)
    if moving:
        appointment.provider_id, appointment.service_id = provider.id, service.id
        appointment.start_time, appointment.end_time = start, end
    appointment.status = target
    if "notes" in data:
        appointment.notes = data["notes"]
    db.flush()
    write_audit_event(db, tenant_id=clinic.tenant_id, clinic_id=clinic.id, action=("appointment.reschedule" if moving else "appointment.update") if existing else "appointment.create",
        entity_type="appointment", entity_id=appointment.id, patient_id=patient.id, actor_type=actor_type, actor_id=actor_id,
        metadata={"clinic_id": clinic.id, "before": before, "after": {"status": target, "start_time": appointment.start_time.isoformat(),
        "end_time": appointment.end_time.isoformat(), "provider_id": appointment.provider_id}})
    return appointment
