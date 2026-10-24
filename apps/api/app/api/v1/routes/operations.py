from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import CallLog, FollowUp, Patient

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/calls")
def list_call_logs(db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    calls = db.query(CallLog).filter(CallLog.clinic_id == clinic.id).order_by(CallLog.created_at.desc()).limit(10).all()
    return {
        "items": [{
            "id": call.id,
            "caller_number": call.caller_number,
            "external_call_id": call.external_call_id,
            "patient_id": call.patient_id,
            "appointment_id": call.appointment_id,
            "escalation_status": call.escalation_status,
            "processed_at": call.processed_at.isoformat() if call.processed_at else None,
            "direction": call.direction,
            "status": call.status,
            "outcome": call.outcome,
            "duration": call.duration,
            "summary": call.summary,
            "start_time": call.start_time.isoformat() if call.start_time else None,
            "created_at": call.created_at.isoformat(),
        } for call in calls]
    }


@router.post("/calls", status_code=status.HTTP_201_CREATED)
def create_call_log(payload: dict, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    call = CallLog(
        tenant_id=clinic.tenant_id,
        clinic_id=clinic.id,
        external_call_id=payload.get("external_call_id"),
        caller_number=payload.get("caller_number"),
        direction=payload.get("direction", "inbound"),
        start_time=payload.get("start_time"),
        end_time=payload.get("end_time"),
        duration=payload.get("duration"),
        status=payload.get("status", "completed"),
        outcome=payload.get("outcome"),
        transcript_reference=payload.get("transcript_reference"),
        summary=payload.get("summary"),
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return {"id": call.id, "status": call.status}


@router.get("/capabilities")
def operation_capabilities(db: Session = Depends(get_db)):
    from app.core.authorization import capabilities
    _, clinic = get_default_tenant_and_clinic(db)
    return {"permissions": capabilities(db), "timezone": clinic.timezone, "currency": clinic.currency}
