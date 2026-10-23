import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, StrictBool
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db
from app.models.models import Appointment, DentalService, FollowUp, Patient, WebhookEvent
from app.services.retell import (verify_signature, integration_context, idempotent_write, call_record, transaction_lock, enforce_function_rate_limit)
from app.services.scheduling import (available_slots_for_day, normalize_datetime, resolve_provider_and_service,
    save_appointment, SchedulingConflictError, ScheduleValidationError, InvalidStatusTransitionError)

router = APIRouter(prefix="/integrations/retell", tags=["retell"])
logger = logging.getLogger(__name__)

class Args(BaseModel):
    model_config = ConfigDict(extra="ignore", str_max_length=500, str_strip_whitespace=True)
    clinic_id: str | None = None
    provider_id: str | None = None
    service_id: str | None = None
    patient_id: str | None = None
    appointment_id: str | None = None
    date: str | None = None
    preferred_date: str | None = None
    time_preference: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    confirmed: StrictBool = False
    idempotency_key: str | None = Field(default=None, max_length=128)
    reason: str | None = None


def result(status, message, success=False, **fields):
    return {"success": success, "status": status, "message": message, **fields}


def process_function(db, payload, integration_id, operation, correlation):
    integration, clinic, call = integration_context(db, payload, integration_id)
    if "args" in payload and not isinstance(payload["args"], dict):
        raise HTTPException(422, "args must be an object")
    try:
        args = Args.model_validate(payload.get("args", payload))
    except ValidationError:
        return result("validation_error", "Function arguments are invalid.")
    if args.clinic_id and args.clinic_id != clinic.id:
        raise HTTPException(403, "Clinic context mismatch")
    call_id = call.get("call_id")
    if call_id is not None and (not isinstance(call_id, str) or len(call_id) > 255):
        raise HTTPException(422, "Invalid call identifier")
    enforce_function_rate_limit(clinic.id, call_id or "information")
    if operation in {"lookup_patient", "verify-patient", "get_appointment", "reschedule_appointment", "cancel_appointment"}:
        # No approved OTP/session-to-call bridge is configured. Never infer identity from LLM args.
        return result("verification_required", "A staff member must verify your identity. Use request_human_assistance to request assistance.",
                      human_assistance_required=True)
    if operation == "check_availability":
        requested = args.preferred_date or args.date
        if not requested:
            return result("validation_error", "preferred_date is required.")
        slots = available_slots_for_day(db, clinic, datetime.fromisoformat(requested), args.provider_id,
                                       args.service_id, args.time_preference)
        return result("available" if slots else "unavailable", "Availability checked.", True,
            timezone=clinic.timezone, slots=[{**s, "start_time": s["start_time"].isoformat(),
                "end_time": s["end_time"].isoformat()} for s in slots])
    if operation == "get_clinic_information":
        return result("found", "Clinic information.", True, clinic={"id": clinic.id, "name": clinic.name,
            "address": clinic.address, "phone": clinic.phone, "timezone": clinic.timezone})
    if operation == "get_treatment_information":
        query = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True))
        if args.service_id:
            query = query.filter(DentalService.id == args.service_id)
        items = [{"id": s.id, "name": s.name, "description": s.description,
                  "default_duration_minutes": s.default_duration_minutes, "indicative_price": s.indicative_price,
                  "currency": s.currency} for s in query.all()]
        return result("found" if items else "not_found", "Approved treatment information.", bool(items),
                      **({"service": items[0]} if args.service_id and items else {"services": items}))
    if not call_id:
        return result("validation_error", "A signed call.call_id is required for writes; disable args-only payloads.")
    if operation == "book_appointment":
        if args.patient_id:
            return result("verification_required", "Staff verification is required to book against an existing patient record.", human_assistance_required=True)
        if not args.confirmed:
            return result("confirmation_required", "Summarize the selected appointment and obtain explicit patient confirmation.")
        if not all((args.first_name, args.last_name, args.phone, args.start_time, args.provider_id, args.service_id)):
            return result("validation_error", "Patient name, phone, provider, service and start_time are required.")
        def book():
            provider, service = resolve_provider_and_service(db, clinic, args.provider_id, args.service_id)
            start = normalize_datetime(args.start_time, ZoneInfo(clinic.timezone or "UTC"))
            end = args.end_time or (start.astimezone(timezone.utc) + timedelta(minutes=service.default_duration_minutes))
            patient = Patient(tenant_id=clinic.tenant_id, clinic_id=clinic.id, first_name=args.first_name,
                              last_name=args.last_name, phone=args.phone)
            db.add(patient)
            db.flush()
            appointment = save_appointment(db, clinic, patient, {"provider_id": provider.id, "service_id": service.id,
                "start_time": start, "end_time": end, "source": "retell"}, "integration", integration.id)
            log = call_record(db, clinic, call_id)
            log.appointment_id, log.outcome = appointment.id, "booked"
            # Patient association remains unset until staff identity verification.
            return result(appointment.status, "Appointment created.", True, appointment_id=appointment.id,
                start_time=appointment.start_time.isoformat(), end_time=appointment.end_time.isoformat(), timezone=clinic.timezone)
        return idempotent_write(db, clinic, call_id, operation, args.idempotency_key, args.model_dump(), book)
    if operation == "create-followup":
        if not args.phone:
            return result("validation_error", "A callback phone number is required.")
        def followup():
            follow = FollowUp(tenant_id=clinic.tenant_id, clinic_id=clinic.id, contact_name=args.first_name,
                              contact_phone=args.phone, reason=args.reason or "Human assistance requested", status="pending")
            db.add(follow)
            db.flush()
            log = call_record(db, clinic, call_id)
            log.outcome, log.escalation_status = "follow_up", "requested"
            return result("created", "Callback request recorded. Staff will review the request; callback timing is not guaranteed.",
                          True, followup_id=follow.id)
        return idempotent_write(db, clinic, call_id, operation, args.idempotency_key, args.model_dump(), followup)
    raise HTTPException(404, "Unknown function")


def function_handler(operation):
    async def endpoint(request: Request, db: Session = Depends(get_db)):
        correlation = str(uuid.uuid4())
        raw = await request.body()
        verify_signature(raw, request.headers.get("x-retell-signature"))
        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError()
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(422, "JSON object required")
        try:
            response = await run_in_threadpool(process_function, db, payload, request.headers.get("x-integration-id"), operation, correlation)
        except (ScheduleValidationError, InvalidStatusTransitionError):
            db.rollback()
            response = result("validation_error", "Requested schedule or function arguments are invalid.")
        except (SchedulingConflictError, IntegrityError):
            db.rollback()
            response = result("unavailable", "The slot is no longer available. Check availability for alternatives.")
        except ValueError:
            db.rollback()
            response = result("validation_error", "Function arguments are invalid.")
        except OperationalError:
            db.rollback()
            response = result("temporary_failure", "The result could not be confirmed. Retry with the same idempotency key.")
        logger.info("retell function=%s correlation=%s status=%s", operation, correlation, response["status"])
        return {**response, "correlation_id": correlation}
    endpoint.__name__ = f"retell_{operation.replace('-', '_')}"
    return endpoint

ALIASES = {
    "check_availability": ["check-availability"], "book_appointment": ["create-appointment"],
    "lookup_patient": ["get-patient"], "verify-patient": [], "get_appointment": ["get-appointment"],
    "reschedule_appointment": ["reschedule-appointment"], "cancel_appointment": ["cancel-appointment"],
    "get_treatment_information": ["get-treatment-information"], "get_clinic_information": ["get-clinic-information"],
    "create-followup": ["request_human_assistance"],
}
for operation, aliases in ALIASES.items():
    handler = function_handler(operation)
    for name in [operation, *aliases]:
        router.add_api_route(f"/functions/{name}", handler, methods=["POST"])


def process_webhook(db, payload):
    _, clinic, call = integration_context(db, payload)
    event = payload.get("event")
    ranks = {"call_started": 1, "call_ended": 2, "call_analyzed": 3}
    if event not in ranks:
        return {"status": "ignored"}
    call_id = call.get("call_id")
    if not isinstance(call_id, str) or not call_id or len(call_id) > 255:
        raise HTTPException(422, "call.call_id is required")
    key = hashlib.sha256(f"{clinic.id}:{call_id}:{event}".encode()).hexdigest()
    transaction_lock(db, f"call:{clinic.id}:{call_id}")
    if db.query(WebhookEvent).filter(WebhookEvent.provider == "retell", WebhookEvent.external_event_id == key).first():
        return {"status": "duplicate"}
    log = call_record(db, clinic, call_id)
    rank = ranks[event]
    if rank >= log.event_rank:
        log.event_rank = rank
        log.status = {1: "ongoing", 2: "ended", 3: "analyzed"}[rank]
    # Fill missing timing fields even when the event arrived out of order; never regress lifecycle/outcome.
    for field, source in (("start_time", "start_timestamp"), ("end_time", "end_timestamp")):
        value = call.get(source)
        if getattr(log, field) is None and isinstance(value, (float, int)) and not isinstance(value, bool):
            try:
                setattr(log, field, datetime.fromtimestamp(value / 1000, timezone.utc))
            except (ValueError, OverflowError, OSError):
                raise HTTPException(422, "Invalid call timestamp")
    if log.start_time and log.end_time:
        from app.services.scheduling import stored_datetime
        log.duration = max(0, int((stored_datetime(log.end_time) - stored_datetime(log.start_time)).total_seconds()))
    if not log.caller_number:
        log.caller_number = call.get("from_number") if call.get("direction") == "inbound" else call.get("to_number")
    if call.get("direction") in {"inbound", "outbound"}:
        log.direction = call["direction"]
    if rank >= 2 and not log.outcome:
        log.outcome = "unresolved"
    log.processed_at = datetime.now(timezone.utc)
    db.add(WebhookEvent(tenant_id=clinic.tenant_id, provider="retell", external_event_id=key,
        processing_status="processed", attempts=1, processed_at=datetime.now(timezone.utc)))
    db.commit()
    return {"status": "accepted", "call_id": call_id}


@router.post("/webhooks")
async def retell_webhook(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    verify_signature(raw, request.headers.get("x-retell-signature"))
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "JSON object required")
    return await run_in_threadpool(process_webhook, db, payload)
