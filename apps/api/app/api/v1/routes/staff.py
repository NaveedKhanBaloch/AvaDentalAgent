from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.routes.auth import get_optional_current_user
from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.core.authorization import ROLE_PERMISSIONS, require_permission as central_require_permission
from app.db.session import get_db
from app.models.models import Membership, User

router = APIRouter(tags=["staff"])

PERMISSIONS_BY_ROLE = ROLE_PERMISSIONS


def require_permission(permission: str):
    return central_require_permission(permission)


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
