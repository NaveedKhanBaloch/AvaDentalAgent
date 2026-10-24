from __future__ import annotations

from fastapi import Depends, HTTPException, status
from contextvars import ContextVar
from app.core.config import get_settings

request_user: ContextVar = ContextVar("request_user", default=None)
from sqlalchemy.orm import Session

from app.api.v1.routes.auth import get_optional_current_user
from app.db.session import get_db
from app.models.models import Clinic, Membership, Tenant, User

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Clinic Owner": ["manage_staff", "manage_schedule", "view_financials", "update_appointments", "create_appointments"],
    "clinic_owner": ["manage_staff", "manage_schedule", "view_financials", "update_appointments", "create_appointments"],
    "receptionist": ["view_patients", "create_appointments", "update_appointments"],
    "dentist": ["view_schedule", "update_appointments"],
    "scheduler": ["manage_schedule", "update_appointments", "create_appointments"],
}


def normalize_role_name(role: str | None) -> str:
    if not role:
        return "receptionist"
    value = role.strip().lower().replace(" ", "_")
    return value


def get_user_membership(db: Session, user_id: str) -> Membership | None:
    return (
        db.query(Membership)
        .filter(Membership.user_id == user_id, Membership.status == "active")
        .order_by(Membership.id.asc())
        .first()
    )


def get_user_default_clinic(db: Session, user: User | None = None) -> tuple[Tenant, Clinic]:
    user = user or request_user.get()
    if user is not None:
        membership = get_user_membership(db, user.id)
        if membership is not None:
            tenant = db.query(Tenant).filter(Tenant.id == membership.tenant_id).first()
            clinic = db.query(Clinic).filter(Clinic.id == membership.clinic_id).first()
            if tenant and clinic and clinic.tenant_id == tenant.id and clinic.status == "active":
                return tenant, clinic

    if user is not None or get_settings().app_env == "production" or get_settings().strict_auth_mode:
        raise HTTPException(status_code=403, detail="An active clinic membership is required.")

    tenant = db.query(Tenant).filter(Tenant.slug == "harbor-dental-demo").first()
    if tenant is None:
        tenant = Tenant(name="Harbor Dental Group", slug="harbor-dental-demo")
        db.add(tenant)
        db.flush()

    clinic = db.query(Clinic).filter(Clinic.tenant_id == tenant.id, Clinic.name == "Harbor Dental Demo").first()
    if clinic is None:
        clinic = Clinic(
            tenant_id=tenant.id,
            name="Harbor Dental Demo",
            address="125 Shoreline Ave",
            city="Boston",
            state="MA",
            country="US",
            timezone="America/New_York",
            phone="(617) 555-0100",
            email="frontdesk@harbordentaldemo.local",
            currency="USD",
        )
        db.add(clinic)
        db.flush()

    return tenant, clinic


def require_permission(permission: str):
    def dependency(current_user: User | None = Depends(get_optional_current_user), db: Session = Depends(get_db)):
        if current_user is None:
            if get_settings().app_env == "production" or get_settings().strict_auth_mode:
                raise HTTPException(status_code=401, detail="Authentication required")
            return None

        membership = get_user_membership(db, current_user.id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires {permission} permission.",
            )

        role = membership.role or "receptionist"
        if permission not in ROLE_PERMISSIONS.get(role, []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires {permission} permission.",
            )
        return current_user

    return dependency


async def bind_request_user(current_user: User | None = Depends(get_optional_current_user)):
    if current_user is None and (get_settings().app_env == "production" or get_settings().strict_auth_mode):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = request_user.set(current_user)
    try:
        yield
    finally:
        request_user.reset(token)


# Phase 2 adds capabilities to existing roles; no new role is introduced.
PHASE2_PERMISSIONS = {
    "clinic_owner": ["patient_read", "patient_write", "patient_archive", "patient_delete", "followup_read", "followup_write", "recall_read", "recall_write", "estimate_read", "estimate_write", "estimate_approve", "estimate_admin", "operations_report"],
    "receptionist": ["patient_read", "patient_write", "patient_archive", "followup_read", "followup_write", "recall_read", "recall_write", "operations_report"],
    "dentist": ["patient_read", "followup_read", "recall_read"],
    "scheduler": ["patient_read", "followup_read", "followup_write", "recall_read", "recall_write", "operations_report"],
}
for _role, _permissions in PHASE2_PERMISSIONS.items():
    ROLE_PERMISSIONS[_role].extend(_permissions)
ROLE_PERMISSIONS["Clinic Owner"].extend(PHASE2_PERMISSIONS["clinic_owner"])


def capabilities(db):
    user = request_user.get()
    if user is None:
        if get_settings().app_env != "production" and not get_settings().strict_auth_mode:
            return ROLE_PERMISSIONS["clinic_owner"]  # Existing explicitly non-strict local demo.
        return []
    membership = get_user_membership(db, user.id)
    return ROLE_PERMISSIONS.get(membership.role, []) if membership else []
