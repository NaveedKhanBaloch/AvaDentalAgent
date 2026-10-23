import hashlib
import hmac
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.core.audit import write_audit_event
from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import Appointment, Clinic, DentalService, Patient, Provider, WebhookEvent

router = APIRouter(prefix="/integrations/retell", tags=["retell"])
settings = get_settings()


def _require_retell_api_access(request: Request) -> None:
    if settings.app_env != "production":
        return

    api_key = request.headers.get("x-retell-api-key") or request.headers.get("authorization", "").replace("Bearer ", "").strip()
    if not api_key or api_key != settings.retell_api_key:
        raise ValueError("Invalid Retell API key.")


def _require_retell_webhook_signature(request: Request, payload: dict) -> None:
    if settings.app_env != "production":
        return

    signature = request.headers.get("x-retell-signature")
    if signature is None:
        raise ValueError("Retell webhook signature is required.")

    expected = hmac.new(
        settings.retell_webhook_secret.encode(),
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Retell webhook signature mismatch.")


def _normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    phone = "".join(ch for ch in str(value) if ch.isdigit() or ch in "+")
    return phone or None


def _find_patient_by_phone(db: Session, clinic_id: str, phone: str | None) -> Patient | None:
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None
    for patient in db.query(Patient).filter(Patient.clinic_id == clinic_id).all():
        if _normalize_phone(patient.phone) == normalized_phone:
            return patient
    return None


def _parse_datetime(value: str | datetime | None, default: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return default
    return default


def _get_default_provider_and_service(db: Session, clinic: Clinic) -> tuple[Provider | None, DentalService | None]:
    provider = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True)).first()
    service = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True)).first()
    return provider, service


@router.post("/functions/check_availability")
@router.post("/functions/check-availability")
def retell_check_availability(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    tenant, clinic = get_default_tenant_and_clinic(db)
    provider_id = payload.get("provider_id")
    service_id = payload.get("service_id")
    requested_date = payload.get("date") or payload.get("start_time")

    provider = None
    if provider_id:
        provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
    if provider is None:
        provider, _ = _get_default_provider_and_service(db, clinic)

    service = None
    if service_id:
        service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
    if service is None:
        _, service = _get_default_provider_and_service(db, clinic)

    start_cursor = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
    if requested_date:
        parsed_date = _parse_datetime(requested_date, start_cursor)
        if parsed_date.date() != datetime.utcnow().date():
            start_cursor = parsed_date.replace(hour=9, minute=0, second=0, microsecond=0)

    slots = []
    for offset in range(0, 6):
        slot_start = start_cursor + timedelta(hours=offset * 2)
        slot_end = slot_start + timedelta(minutes=(service.default_duration_minutes if service else 30))
        conflict = db.query(Appointment).filter(
            Appointment.clinic_id == clinic.id,
            Appointment.provider_id == provider.id if provider else Appointment.provider_id.isnot(None),
            Appointment.status != "cancelled",
            Appointment.start_time < slot_end,
            Appointment.end_time > slot_start,
        ).first()
        if not conflict:
            slots.append({"start_time": slot_start.isoformat(), "end_time": slot_end.isoformat()})

    return {"success": True, "status": "available", "slots": slots, "message": "Availability checked.", "clinic_id": clinic.id, "tenant_id": tenant.id}


@router.post("/functions/book_appointment")
@router.post("/functions/create-appointment")
def retell_create_appointment(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    tenant, clinic = get_default_tenant_and_clinic(db)
    patient_id = payload.get("patient_id")
    if not patient_id:
        phone = _normalize_phone(payload.get("phone"))
        email = str(payload.get("email") or "").strip().lower() or None
        patient = None
        if email:
            patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.email == email).first()
        if patient is None:
            patient = _find_patient_by_phone(db, clinic.id, phone)
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
        patient_id = patient.id

    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.clinic_id == clinic.id).first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    provider_id = payload.get("provider_id")
    provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first() if provider_id else None
    if provider is None:
        provider, _ = _get_default_provider_and_service(db, clinic)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No provider is configured for this clinic.")

    service_id = payload.get("service_id")
    service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first() if service_id else None
    if service is None:
        _, service = _get_default_provider_and_service(db, clinic)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No service is configured for this clinic.")

    start_time = _parse_datetime(payload.get("start_time"), datetime.utcnow() + timedelta(hours=1))
    end_time = _parse_datetime(payload.get("end_time"), start_time + timedelta(minutes=service.default_duration_minutes))

    overlap = db.query(Appointment).filter(
        Appointment.clinic_id == clinic.id,
        Appointment.provider_id == provider.id,
        Appointment.status != "cancelled",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    ).first()
    if overlap:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Requested appointment overlaps with an existing visit.")

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
        notes=str(payload.get("notes") or "Booked through Retell voice agent."),
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    write_audit_event(
        db,
        tenant_id=tenant.id,
        clinic_id=clinic.id,
        action="retell.appointment.create",
        entity_type="appointment",
        entity_id=appointment.id,
        actor_type="integration",
        metadata={"source": "retell"},
    )
    return {"success": True, "status": appointment.status, "appointment_id": appointment.id, "message": "Appointment created."}


@router.post("/functions/verify-patient")
def retell_verify_patient(payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    payload = payload or {}
    _, clinic = get_default_tenant_and_clinic(db)
    phone = _normalize_phone(payload.get("phone"))
    email = str(payload.get("email") or "").strip().lower() or None
    patient = None
    if email:
        patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.email == email).first()
    if patient is None:
        patient = _find_patient_by_phone(db, clinic.id, phone)
    if patient is None:
        return {"success": False, "status": "not_found", "message": "Patient not found."}
    return {"success": True, "status": "verified", "patient_id": patient.id, "patient": {"first_name": patient.first_name, "last_name": patient.last_name, "phone": patient.phone, "email": patient.email}}


@router.post("/functions/lookup_patient")
@router.post("/functions/get-patient")
def retell_lookup_patient(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    _, clinic = get_default_tenant_and_clinic(db)
    phone = _normalize_phone(payload.get("phone"))
    email = str(payload.get("email") or "").strip().lower() or None
    first_name = str(payload.get("first_name") or payload.get("firstName") or "").strip()
    last_name = str(payload.get("last_name") or payload.get("lastName") or "").strip()

    patient = None
    if email:
        patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.email == email).first()
    if patient is None:
        patient = _find_patient_by_phone(db, clinic.id, phone)
    if patient is None and first_name and last_name:
        patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.first_name == first_name, Patient.last_name == last_name).first()
    if patient is None:
        return {"success": False, "status": "not_found", "message": "Patient not found."}

    return {"success": True, "status": "found", "patient": {"id": patient.id, "first_name": patient.first_name, "last_name": patient.last_name, "phone": patient.phone, "email": patient.email, "preferred_contact_method": patient.preferred_contact_method}}


@router.post("/functions/get-appointment")
@router.post("/functions/get_appointment")
def retell_get_appointment(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    _, clinic = get_default_tenant_and_clinic(db)
    appointment_id = payload.get("appointment_id")
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.clinic_id == clinic.id).first()
    if appointment is None:
        return {"success": False, "status": "not_found", "message": "Appointment not found."}
    return {"success": True, "status": "found", "appointment": {"id": appointment.id, "status": appointment.status, "start_time": appointment.start_time.isoformat(), "end_time": appointment.end_time.isoformat()}}


@router.post("/functions/reschedule_appointment")
@router.post("/functions/reschedule-appointment")
def retell_reschedule_appointment(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    _, clinic = get_default_tenant_and_clinic(db)
    appointment_id = payload.get("appointment_id")
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.clinic_id == clinic.id).first()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    start_time = _parse_datetime(payload.get("start_time"), appointment.start_time)
    end_time = _parse_datetime(payload.get("end_time"), start_time + timedelta(minutes=30))
    appointment.start_time = start_time
    appointment.end_time = end_time
    appointment.status = str(payload.get("status") or appointment.status).lower()
    appointment.notes = str(payload.get("notes") or appointment.notes or "Rescheduled by Retell voice agent.")
    db.commit()
    return {"success": True, "status": "rescheduled", "appointment_id": appointment.id, "message": "Appointment updated."}


@router.post("/functions/cancel_appointment")
@router.post("/functions/cancel-appointment")
def retell_cancel_appointment(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    _, clinic = get_default_tenant_and_clinic(db)
    appointment_id = payload.get("appointment_id")
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id, Appointment.clinic_id == clinic.id).first()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    appointment.status = "cancelled"
    db.commit()
    return {"success": True, "status": "cancelled", "appointment_id": appointment.id, "message": "Appointment cancelled."}


@router.post("/functions/create-followup")
def retell_create_followup() -> dict:
    return {"success": True, "status": "created", "followup_id": "demo-followup"}


@router.post("/functions/get_treatment_information")
@router.post("/functions/get-treatment-information")
def retell_get_treatment_information(request: Request, payload: dict | None = None, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    payload = payload or {}
    _, clinic = get_default_tenant_and_clinic(db)
    service_id = payload.get("service_id")
    if service_id:
        service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
        if service:
            return {"success": True, "status": "found", "service": {"id": service.id, "name": service.name, "description": service.description, "default_duration_minutes": service.default_duration_minutes, "indicative_price": service.indicative_price, "currency": service.currency}}
        return {"success": False, "status": "not_found", "message": "Treatment not found."}

    services = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True)).all()
    return {"success": True, "status": "available", "services": [{"id": item.id, "name": item.name, "description": item.description, "default_duration_minutes": item.default_duration_minutes, "indicative_price": item.indicative_price} for item in services]}


@router.post("/functions/get_clinic_information")
@router.post("/functions/get-clinic-information")
def retell_get_clinic_information(request: Request, db: Session = Depends(get_db)) -> dict:
    try:
        _require_retell_api_access(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    _, clinic = get_default_tenant_and_clinic(db)
    return {
        "success": True,
        "status": "found",
        "clinic": {
            "id": clinic.id,
            "name": clinic.name,
            "address": clinic.address,
            "city": clinic.city,
            "state": clinic.state,
            "country": clinic.country,
            "phone": clinic.phone,
            "email": clinic.email,
            "timezone": clinic.timezone,
        },
    }


@router.post("/webhooks")
def retell_webhook(request: Request, payload: dict, db: Session = Depends(get_db)) -> dict:
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Retell webhook payload is required.")

    try:
        _require_retell_api_access(request)
        _require_retell_webhook_signature(request, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    external_event_id = str(payload.get("id") or payload.get("event_id") or payload.get("call_id") or "").strip()
    if external_event_id:
        existing = db.query(WebhookEvent).filter(WebhookEvent.provider == "retell", WebhookEvent.external_event_id == external_event_id).first()
        if existing:
            return {"status": "duplicate", "message": "Retell webhook already processed."}

    patient_payload = payload.get("patient") or {}
    tenant, clinic = get_default_tenant_and_clinic(db)

    phone = _normalize_phone(str(patient_payload.get("phone") or payload.get("phone") or "").strip())
    email = str(patient_payload.get("email") or payload.get("email") or "").strip() or None
    first_name = str(patient_payload.get("first_name") or patient_payload.get("firstName") or payload.get("first_name") or "New").strip()
    last_name = str(patient_payload.get("last_name") or patient_payload.get("lastName") or payload.get("last_name") or "Patient").strip()

    patient = None
    if email:
        patient = db.query(Patient).filter(Patient.clinic_id == clinic.id, Patient.email == email).first()
    if patient is None:
        patient = _find_patient_by_phone(db, clinic.id, phone)
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
    start_time = _parse_datetime(start_time_value, datetime.utcnow() + timedelta(hours=1))
    end_time = _parse_datetime(end_time_value, start_time + timedelta(minutes=service.default_duration_minutes))

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

    if external_event_id:
        db.add(
            WebhookEvent(
                tenant_id=tenant.id,
                provider="retell",
                external_event_id=external_event_id,
                payload_reference=json.dumps(payload, default=str),
                processing_status="processed",
                attempts=1,
            )
        )
        db.commit()

    write_audit_event(
        db,
        tenant_id=tenant.id,
        clinic_id=clinic.id,
        action="retell.webhook.booking",
        entity_type="appointment",
        entity_id=appointment.id,
        actor_type="integration",
        metadata={"source": "retell", "webhook_event_id": external_event_id},
    )
    return {"status": "accepted", "appointment_id": appointment.id, "message": "Retell booking captured into the clinic schedule."}
