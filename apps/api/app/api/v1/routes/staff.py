from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.routes.auth import get_optional_current_user
from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import Membership, User

router = APIRouter(tags=["staff"])

PERMISSIONS_BY_ROLE = {
    "Clinic Owner": ["manage_staff", "manage_schedule", "view_financials", "update_appointments", "create_appointments"],
    "clinic_owner": ["manage_staff", "manage_schedule", "view_financials", "update_appointments", "create_appointments"],
    "receptionist": ["view_patients", "create_appointments", "update_appointments"],
    "dentist": ["view_schedule", "update_appointments"],
    "scheduler": ["manage_schedule", "update_appointments", "create_appointments"],
}


def require_permission(permission: str):
    def dependency(current_user: User | None = Depends(get_optional_current_user), db: Session = Depends(get_db)) -> User | None:
        if current_user is None:
            return None

        membership = db.query(Membership).filter(Membership.user_id == current_user.id).order_by(Membership.id.asc()).first()
        role = membership.role if membership else "clinic_owner"
        allowed = permission in PERMISSIONS_BY_ROLE.get(role, [])
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission denied: requires {permission} permission.")
        return current_user

    return dependency


@router.get("/staff")
def list_staff(db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    memberships = db.query(Membership).filter(Membership.clinic_id == clinic.id, Membership.status == "active").order_by(Membership.role.asc()).all()
    items: list[dict] = []

    for membership in memberships:
        user = db.query(User).filter(User.id == membership.user_id).first()
        permissions = PERMISSIONS_BY_ROLE.get(membership.role, ["view_schedule"])
        items.append({
            "id": membership.id,
            "user_id": membership.user_id,
            "full_name": user.full_name if user else "Unknown staff member",
            "email": user.email if user else None,
            "role": membership.role,
            "status": membership.status,
            "permissions": permissions,
        })

    return {"items": items}
