from __future__ import annotations

from fastapi import Depends, HTTPException, status
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
    if user is not None:
        membership = get_user_membership(db, user.id)
        if membership is not None:
            tenant = db.query(Tenant).filter(Tenant.id == membership.tenant_id).first()
            clinic = db.query(Clinic).filter(Clinic.id == membership.clinic_id).first()
            if tenant and clinic:
                return tenant, clinic

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
