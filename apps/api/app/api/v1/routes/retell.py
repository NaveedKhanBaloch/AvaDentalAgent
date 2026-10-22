from fastapi import APIRouter, HTTPException, status

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
def retell_webhook() -> dict:
    return {"status": "accepted"}
