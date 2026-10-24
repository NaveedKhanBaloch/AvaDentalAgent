from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import AuditLog


def write_audit_event(
    db: Session,
    *,
    tenant_id: str | None,
    clinic_id: str | None,
    action: str,
    patient_id: str | None = None,
    entity_type: str,
    entity_id: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog | None:
    if tenant_id is None or clinic_id is None:
        return None

    entry = AuditLog(
        tenant_id=tenant_id,
        clinic_id=clinic_id,
        patient_id=patient_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        audit_metadata=json.dumps(metadata, default=str) if metadata else None,
    )
    db.add(entry)
    db.flush()
    return entry
