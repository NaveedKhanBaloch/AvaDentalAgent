import json
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.core.authorization import request_user
from app.models.models import (
    Clinic,
    DentalService,
    EstimateAcknowledgement,
    EstimateItem,
    EstimatePolicy,
    EstimateStatusHistory,
    EstimateVersion,
    Patient,
    TreatmentEstimate,
)
from app.services.patient_operations import check_revision, event, scoped


def policy_for(db, clinic):
    p = db.get(EstimatePolicy, clinic.id)
    if not p:
        raise HTTPException(
            409, "Configure and approve the clinic estimate policy before creating an estimate"
        )
    return p


def calculate(db, clinic, lines, policy):
    quantum = Decimal(1).scaleb(-policy.minor_units)
    rates = {k: Decimal(str(v)) for k, v in json.loads(policy.tax_rates).items()}
    services = {
        s.id: s
        for s in db.query(DentalService).filter(
            DentalService.clinic_id == clinic.id,
            DentalService.active_status.is_(True),
            DentalService.id.in_([r.service_id for r in lines]),
        )
    }
    result = []

    def money(v):
        if not v.is_finite() or abs(v) >= Decimal(10000000000000):
            raise HTTPException(422, "Financial amount exceeds supported range")
        return v.quantize(quantum, rounding=ROUND_HALF_UP)

    for pos, line in enumerate(lines):
        service = services.get(line.service_id)
        if not service or service.currency != policy.currency:
            raise HTTPException(
                422, "Treatment is unavailable or currency differs from clinic policy"
            )
        if line.discount_percent > policy.max_discount_percent:
            raise HTTPException(422, "Discount exceeds clinic policy")
        if line.tax_label not in rates:
            raise HTTPException(422, "Tax label has not been approved for this clinic")
        # The legacy float is converted once via its decimal text, then snapshotted in Numeric.
        price = (
            line.unit_price
            if line.unit_price is not None
            else Decimal(str(service.indicative_price))
        )
        if not price.is_finite() or price < 0:
            raise HTTPException(422, "Catalog price must be a finite nonnegative amount")
        price = price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        subtotal = money(price * line.quantity)
        discount = money(subtotal * line.discount_percent / 100)
        tax = money((subtotal - discount) * rates[line.tax_label] / 100)
        result.append(
            {
                "service_id": service.id,
                "description": service.name
                + (("\n" + service.description) if service.description else ""),
                "quantity": line.quantity,
                "unit_price": price,
                "discount_percent": line.discount_percent,
                "tax_label": line.tax_label,
                "tax_rate": rates[line.tax_label],
                "subtotal": subtotal,
                "discount": discount,
                "tax": tax,
                "total": money(subtotal - discount + tax),
                "position": pos,
            }
        )
    totals = {
        k: sum((r[k] for r in result), Decimal(0)) for k in ("subtotal", "discount", "tax", "total")
    }
    if any(v >= Decimal(100000000000000) for v in totals.values()):
        raise HTTPException(422, "Estimate total exceeds supported range")
    return result, totals


def version_for(db, estimate, version=None):
    v = (
        db.query(EstimateVersion)
        .filter_by(estimate_id=estimate.id, version=version or estimate.current_version)
        .first()
    )
    if not v:
        raise HTTPException(404, "Estimate version not found")
    return v


def history(db, clinic, estimate, version, previous, status, reason=None):
    user = request_user.get()
    db.add(
        EstimateStatusHistory(
            estimate_id=estimate.id,
            version_id=version.id,
            previous_status=previous,
            status=status,
            actor_id=user.id if user else None,
            reason=reason,
        )
    )
    event(db, clinic, "estimate." + status, estimate, estimate.patient_id)


def save_draft(db, clinic, payload, estimate=None, revision=False):
    patient = scoped(db, Patient, payload.patient_id, clinic)
    if patient.status != "active":
        raise HTTPException(409, "Restore archived patient before creating or editing an estimate")
    policy = policy_for(db, clinic)
    if payload.valid_until and payload.valid_until < payload.issue_date:
        raise HTTPException(422, "Expiry cannot precede issue date")
    if estimate:
        check_revision(estimate, payload.expected_revision)
        if payload.expected_revision is None:
            raise HTTPException(422, "expected_revision required")
        if estimate.patient_id != patient.id:
            raise HTTPException(422, "Estimate patient cannot be changed")
        if revision:
            if estimate.status == "draft":
                raise HTTPException(409, "Edit the current draft rather than revising it")
            if not payload.revision_reason or not payload.revision_reason.strip():
                raise HTTPException(422, "A revision reason is required")
            estimate.current_version += 1
        elif estimate.status != "draft":
            raise HTTPException(409, "Issued estimate content is immutable; create a revision")
        estimate.revision += 1
    else:
        db.query(Clinic).filter_by(id=clinic.id).with_for_update().first()
        number = f"EST-{datetime.now(timezone.utc).year}-{db.query(TreatmentEstimate).filter_by(clinic_id=clinic.id).count()+1:06d}"
        user = request_user.get()
        estimate = TreatmentEstimate(
            tenant_id=clinic.tenant_id,
            clinic_id=clinic.id,
            patient_id=patient.id,
            number=number,
            created_by=user.id if user else None,
        )
        db.add(estimate)
        db.flush()
    items, totals = calculate(db, clinic, payload.items, policy)
    v = (
        db.query(EstimateVersion)
        .filter_by(estimate_id=estimate.id, version=estimate.current_version)
        .first()
    )
    is_new = v is None
    if not v:
        v = EstimateVersion(
            estimate_id=estimate.id,
            version=estimate.current_version,
            created_by=estimate.created_by,
        )
        db.add(v)
    else:
        db.query(EstimateItem).filter_by(version_id=v.id).delete()
    previous = estimate.status
    estimate.status = "draft"
    v.status = "draft"
    v.currency = policy.currency
    v.minor_units = policy.minor_units
    for key, value in totals.items():
        setattr(v, key, value)
    v.issue_date = payload.issue_date
    v.valid_until = payload.valid_until or (
        payload.issue_date + timedelta(days=policy.validity_days) if policy.validity_days else None
    )
    v.terms = policy.terms
    v.revision_reason = payload.revision_reason
    v.policy_snapshot = json.dumps(
        {
            "tax_rates": json.loads(policy.tax_rates),
            "max_discount_percent": str(policy.max_discount_percent),
            "rounding": "ROUND_HALF_UP",
            "policy_revision": policy.revision,
        }
    )
    v.clinic_snapshot = json.dumps(
        {
            k: getattr(clinic, k)
            for k in ("name", "address", "city", "state", "country", "phone", "email")
        }
    )
    v.patient_snapshot = json.dumps({"name": patient.first_name + " " + patient.last_name})
    user = request_user.get()
    if is_new:
        v.created_by = user.id if user else None
    db.flush()
    db.add_all([EstimateItem(version_id=v.id, **item) for item in items])
    db.flush()
    history(
        db,
        clinic,
        estimate,
        v,
        previous,
        "draft",
        "Revision: " + payload.revision_reason if revision else "Draft saved",
    )
    return estimate


def transition(db, clinic, estimate, payload):
    check_revision(estimate, payload.expected_revision)
    if payload.version != estimate.current_version:
        raise HTTPException(409, "Acknowledgement/action must refer to current version")
    if not payload.confirmed:
        raise HTTPException(422, "Explicit confirmation required")
    allowed = {
        "draft": {"sent", "cancelled"},
        "sent": {"accepted", "declined", "expired", "cancelled"},
        "accepted": set(),
        "declined": set(),
        "expired": set(),
        "cancelled": set(),
    }
    if payload.status not in allowed[estimate.status]:
        raise HTTPException(409, "Invalid estimate status transition")
    v = version_for(db, estimate)
    if payload.status == "sent" and not (payload.method and payload.method.strip()):
        raise HTTPException(
            422,
            "Record how the estimate was delivered externally; no message is sent by this application",
        )
    if payload.status in {"accepted", "declined"}:
        if (
            not payload.acknowledged_by_name
            or not payload.acknowledged_by_name.strip()
            or not payload.method
        ):
            raise HTTPException(
                422, "Patient/representative name and acknowledgement method required"
            )
        db.add(
            EstimateAcknowledgement(
                version_id=v.id,
                decision=payload.status,
                acknowledged_by_name=payload.acknowledged_by_name,
                method=payload.method,
                recorded_by=request_user.get().id if request_user.get() else None,
            )
        )
    if payload.status == "expired" and (
        not v.valid_until
        or v.valid_until >= datetime.now(ZoneInfo(clinic.timezone or "UTC")).date()
    ):
        raise HTTPException(409, "Estimate has not expired")
    previous = estimate.status
    estimate.status = payload.status
    v.status = payload.status
    estimate.revision += 1
    history(db, clinic, estimate, v, previous, payload.status, payload.reason or payload.method)
    db.flush()
    return estimate


def decimal_row(row):
    return {
        c.name: (
            str(getattr(row, c.name))
            if isinstance(getattr(row, c.name), Decimal)
            else getattr(row, c.name)
        )
        for c in row.__table__.columns
    }


def detail(db, estimate, number=None, version_page=1, history_page=1):
    v = version_for(db, estimate, number)
    versions = (
        db.query(EstimateVersion)
        .filter_by(estimate_id=estimate.id)
        .order_by(EstimateVersion.version.desc())
        .offset((version_page - 1) * 25)
        .limit(25)
        .all()
    )
    histories = (
        db.query(EstimateStatusHistory)
        .filter_by(estimate_id=estimate.id)
        .order_by(EstimateStatusHistory.created_at.desc())
        .offset((history_page - 1) * 25)
        .limit(25)
        .all()
    )
    ack = db.query(EstimateAcknowledgement).filter_by(version_id=v.id).first()
    return {
        **decimal_row(estimate),
        "version": v.version,
        "version_page": version_page,
        "history_page": history_page,
        "version_total": db.query(EstimateVersion).filter_by(estimate_id=estimate.id).count(),
        "history_total": db.query(EstimateStatusHistory).filter_by(estimate_id=estimate.id).count(),
        "document": decimal_row(v),
        "items": [
            decimal_row(r)
            for r in db.query(EstimateItem)
            .filter_by(version_id=v.id)
            .order_by(EstimateItem.position)
        ],
        "versions": [
            {
                "version": r.version,
                "status": r.status,
                "total": str(r.total),
                "currency": r.currency,
                "created_at": r.created_at,
                "reason": r.revision_reason,
            }
            for r in versions
        ],
        "history": [decimal_row(r) for r in histories],
        "acknowledgement": decimal_row(ack) if ack else None,
    }
