import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.authorization import get_user_default_clinic, request_user, require_permission
from app.db.session import get_db
from app.models.models import (
    EstimatePolicy,
    EstimateVersion,
    Patient,
    TreatmentEstimate,
)
from app.schemas.estimate import EstimateAction, EstimateDraft, PolicyInput
from app.services.estimates import (
    calculate,
    decimal_row,
    detail,
    policy_for,
    save_draft,
    transition,
)
from app.services.patient_operations import check_revision, page_query, scoped

router = APIRouter(
    prefix="/estimates",
    tags=["treatment estimates"],
    dependencies=[Depends(require_permission("estimate_read"))],
)


@router.get("/policy")
def get_policy(db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    p = db.get(EstimatePolicy, clinic.id)
    return (
        dict(decimal_row(p), tax_rates=json.loads(p.tax_rates))
        if p
        else {"configured": False, "currency": clinic.currency}
    )


@router.put("/policy", dependencies=[Depends(require_permission("estimate_admin"))])
def set_policy(payload: PolicyInput, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    user = request_user.get()
    if not user or not payload.clinically_approved:
        raise HTTPException(422, "Authenticated policy approval is required")
    if payload.currency != clinic.currency:
        raise HTTPException(422, "Policy currency must match the clinic currency")
    p = db.query(EstimatePolicy).filter_by(clinic_id=clinic.id).with_for_update().first()
    if p:
        if payload.expected_revision is None:
            raise HTTPException(422, "expected_revision required")
        check_revision(p, payload.expected_revision)
        p.revision += 1
    else:
        p = EstimatePolicy(clinic_id=clinic.id)
        db.add(p)
    for key in ("currency", "minor_units", "max_discount_percent", "terms", "validity_days"):
        setattr(p, key, getattr(payload, key))
    p.tax_rates = json.dumps({k: str(v) for k, v in payload.tax_rates.items()})
    p.approved_by = user.id
    from datetime import datetime, timezone

    p.approved_at = datetime.now(timezone.utc)
    from app.core.audit import write_audit_event

    write_audit_event(
        db,
        tenant_id=clinic.tenant_id,
        clinic_id=clinic.id,
        action="estimate_policy.approved",
        entity_type="estimate_policy",
        entity_id=clinic.id,
        actor_type="user",
        actor_id=user.id,
    )
    db.commit()
    return get_policy(db)


@router.post("/preview", dependencies=[Depends(require_permission("estimate_write"))])
def preview(payload: EstimateDraft, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    scoped(db, Patient, payload.patient_id, clinic)
    lines, totals = calculate(db, clinic, payload.items, policy_for(db, clinic))
    return {
        "items": [
            {k: str(v) if hasattr(v, "as_tuple") else v for k, v in r.items()} for r in lines
        ],
        **{k: str(v) for k, v in totals.items()},
    }


@router.get("")
def listing(
    search: str | None = None,
    status: str | None = None,
    patient_id: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    sort: str = "created_at",
    direction: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _, clinic = get_user_default_clinic(db)
    query = (
        db.query(TreatmentEstimate, EstimateVersion, Patient)
        .join(
            EstimateVersion,
            (EstimateVersion.estimate_id == TreatmentEstimate.id)
            & (EstimateVersion.version == TreatmentEstimate.current_version),
        )
        .join(Patient, Patient.id == TreatmentEstimate.patient_id)
        .filter(TreatmentEstimate.clinic_id == clinic.id)
    )
    if search:
        term = "%" + search + "%"
        query = query.filter(
            or_(
                TreatmentEstimate.number.ilike(term),
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
            )
        )
    if status:
        query = query.filter(TreatmentEstimate.status == status)
    if patient_id:
        query = query.filter(TreatmentEstimate.patient_id == patient_id)
    if created_from:
        query = query.filter(TreatmentEstimate.created_at >= created_from)
    if created_to:
        from datetime import timedelta

        query = query.filter(TreatmentEstimate.created_at < created_to + timedelta(days=1))
    sorts = {
        "created_at": TreatmentEstimate.created_at,
        "number": TreatmentEstimate.number,
        "total": EstimateVersion.total,
    }
    if sort not in sorts or direction not in {"asc", "desc"}:
        raise HTTPException(422, "Invalid sort")
    rows, total = page_query(
        query.order_by(
            sorts[sort].desc() if direction == "desc" else sorts[sort].asc(), TreatmentEstimate.id
        ),
        page,
        page_size,
    )
    return {
        "items": [
            dict(
                decimal_row(e),
                version=v.version,
                total=str(v.total),
                currency=v.currency,
                patient_name=p.first_name + " " + p.last_name,
            )
            for e, v, p in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201, dependencies=[Depends(require_permission("estimate_write"))])
def create(payload: EstimateDraft, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    e = save_draft(db, clinic, payload)
    db.commit()
    return detail(db, e)


@router.get("/{estimate_id}")
def get_estimate(
    estimate_id: str,
    version: int | None = Query(None, ge=1),
    version_page: int = Query(1, ge=1),
    history_page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    _, clinic = get_user_default_clinic(db)
    return detail(
        db, scoped(db, TreatmentEstimate, estimate_id, clinic), version, version_page, history_page
    )


@router.patch("/{estimate_id}", dependencies=[Depends(require_permission("estimate_write"))])
def update(estimate_id: str, payload: EstimateDraft, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    e = save_draft(db, clinic, payload, scoped(db, TreatmentEstimate, estimate_id, clinic, True))
    db.commit()
    return detail(db, e)


@router.post(
    "/{estimate_id}/revisions", dependencies=[Depends(require_permission("estimate_admin"))]
)
def revise(estimate_id: str, payload: EstimateDraft, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    e = save_draft(
        db, clinic, payload, scoped(db, TreatmentEstimate, estimate_id, clinic, True), True
    )
    db.commit()
    return detail(db, e)


@router.post(
    "/{estimate_id}/duplicate", dependencies=[Depends(require_permission("estimate_write"))]
)
def duplicate(estimate_id: str, db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    original = scoped(db, TreatmentEstimate, estimate_id, clinic)
    d = detail(db, original)
    from datetime import date

    payload = EstimateDraft(
        patient_id=original.patient_id,
        issue_date=date.today(),
        items=[
            {
                k: r[k]
                for k in ("service_id", "quantity", "unit_price", "discount_percent", "tax_label")
            }
            for r in d["items"]
        ],
    )
    e = save_draft(db, clinic, payload)
    db.commit()
    return detail(db, e)


@router.post("/{estimate_id}/status", dependencies=[Depends(require_permission("estimate_write"))])
def status_action(estimate_id: str, payload: EstimateAction, db: Session = Depends(get_db)):
    if payload.status in {"accepted", "declined"}:
        from app.core.authorization import capabilities

        if "estimate_approve" not in capabilities(db):
            raise HTTPException(403, "Estimate approval permission required")
    _, clinic = get_user_default_clinic(db)
    e = transition(db, clinic, scoped(db, TreatmentEstimate, estimate_id, clinic, True), payload)
    db.commit()
    return detail(db, e)


@router.get("/{estimate_id}/pdf")
def pdf(estimate_id: str, version: int | None = Query(None, ge=1), db: Session = Depends(get_db)):
    _, clinic = get_user_default_clinic(db)
    e = scoped(db, TreatmentEstimate, estimate_id, clinic)
    from app.services.estimate_pdf import render_pdf

    data = render_pdf(db, e, version)
    return Response(
        data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{e.number}-v{version or e.current_version}.pdf"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
