import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import DentalService, Patient

client = TestClient(app)


def owner():
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@harbordentaldemo.local", "password": "AdminPass123!"},
    ).json()["access_token"]
    return {"Authorization": "Bearer " + token}


def policy():
    r = client.put(
        "/api/v1/estimates/policy",
        headers=owner(),
        json={
            "currency": "USD",
            "minor_units": 2,
            "tax_rates": {"none": "0", "standard": "10"},
            "max_discount_percent": "20",
            "terms": "Administrative estimate only.",
            "validity_days": 30,
            "clinically_approved": True,
        },
    )
    assert r.status_code == 200, r.text


def draft():
    with SessionLocal() as db:
        p = db.query(Patient).first()
        s = db.query(DentalService).first()
    return {
        "patient_id": p.id,
        "issue_date": "2026-10-24",
        "items": [
            {
                "service_id": s.id,
                "quantity": "3",
                "unit_price": "0.10",
                "discount_percent": "10",
                "tax_label": "standard",
            }
        ],
    }


def test_decimal_totals_versions_acknowledgement_pdf():
    policy()
    body = draft()
    r = client.post("/api/v1/estimates", json=body)
    assert r.status_code == 201, r.text
    d = r.json()
    eid = d["id"]
    assert d["document"]["total"] == "0.3000"
    assert d["document"]["discount"] == "0.0300" and d["document"]["tax"] == "0.0300"
    sent = client.post(
        f"/api/v1/estimates/{eid}/status",
        json={
            "expected_revision": 1,
            "version": 1,
            "status": "sent",
            "confirmed": True,
            "method": "Printed copy delivered in clinic",
        },
    ).json()
    accepted = client.post(
        f"/api/v1/estimates/{eid}/status",
        json={
            "expected_revision": 2,
            "version": 1,
            "status": "accepted",
            "confirmed": True,
            "method": "In-clinic confirmation recorded by staff",
            "acknowledged_by_name": "Synthetic Patient",
        },
    )
    assert accepted.status_code == 200, accepted.text
    assert (
        client.patch(f"/api/v1/estimates/{eid}", json={**body, "expected_revision": 3}).status_code
        == 409
    )
    revised = client.post(
        f"/api/v1/estimates/{eid}/revisions",
        json={
            **body,
            "expected_revision": 3,
            "revision_reason": "Patient requested another option",
        },
    )
    assert revised.status_code == 200, revised.text
    old = client.get(f"/api/v1/estimates/{eid}?version=1").json()
    assert (
        old["document"]["status"] == "accepted" and old["acknowledgement"]["decision"] == "accepted"
    )
    assert revised.json()["current_version"] == 2
    pdf = client.get(f"/api/v1/estimates/{eid}/pdf?version=1")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    from pypdf import PdfReader

    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "0.30" in text and "Version 1" in text


def test_policy_required_validation_and_concurrent_revision_guard():
    assert client.post("/api/v1/estimates", json=draft()).status_code == 409
    policy()
    body = draft()
    d = client.post("/api/v1/estimates", json=body).json()
    update = {**body, "expected_revision": 1}
    assert client.patch("/api/v1/estimates/" + d["id"], json=update).status_code == 200
    assert client.patch("/api/v1/estimates/" + d["id"], json=update).status_code == 409
    body["items"][0]["discount_percent"] = "21"
    assert client.post("/api/v1/estimates", json=body).status_code == 422
    body["items"][0]["quantity"] = "NaN"
    assert client.post("/api/v1/estimates", json=body).status_code == 422


def test_estimate_permissions_and_scoped_pdf():
    from app.core.security import create_access_token
    from app.models.models import User, Membership, Clinic, Tenant

    policy()
    estimate = client.post("/api/v1/estimates", json=draft()).json()
    with SessionLocal() as db:
        clinic = db.query(Clinic).first()
        receptionist = User(
            email="receptionist@example.com", full_name="Receptionist", password_hash="unused"
        )
        db.add(receptionist)
        db.flush()
        db.add(
            Membership(
                user_id=receptionist.id,
                clinic_id=clinic.id,
                tenant_id=clinic.tenant_id,
                role="receptionist",
            )
        )
        tenant = Tenant(name="Other", slug="estimate-other")
        db.add(tenant)
        db.flush()
        other = Clinic(name="Other", tenant_id=tenant.id)
        db.add(other)
        db.flush()
        owner_user = User(
            email="other-owner@example.com", full_name="Other", password_hash="unused"
        )
        db.add(owner_user)
        db.flush()
        db.add(
            Membership(
                user_id=owner_user.id, tenant_id=tenant.id, clinic_id=other.id, role="clinic_owner"
            )
        )
        db.commit()
    h = {"Authorization": "Bearer " + create_access_token(receptionist.id)}
    assert client.get("/api/v1/estimates", headers=h).status_code == 403
    assert client.get(f"/api/v1/estimates/{estimate['id']}/pdf", headers=h).status_code == 403
    metrics = client.get("/api/v1/operations/metrics", headers=h).json()
    assert not any(k.startswith("estimates_") for k in metrics)
    timeline = client.get(
        "/api/v1/patients/" + estimate["patient_id"] + "/timeline", headers=h
    ).json()["items"]
    assert not any(i["event_type"].startswith("estimate.") for i in timeline)
    assert (
        client.get(
            f"/api/v1/estimates/{estimate['id']}/pdf",
            headers={"Authorization": "Bearer " + create_access_token(owner_user.id)},
        ).status_code
        == 404
    )


def test_large_pdf_escapes_text_and_preserves_all_lines():
    from pypdf import PdfReader

    policy()
    body = draft()
    with SessionLocal() as db:
        service = db.get(DentalService, body["items"][0]["service_id"])
        service.description = "Synthetic <review> & administrative description. " * 8
        db.commit()
    body["items"] = body["items"] * 60
    r = client.post("/api/v1/estimates", json=body)
    assert r.status_code == 201, r.text
    pdf = client.get("/api/v1/estimates/" + r.json()["id"] + "/pdf")
    reader = PdfReader(io.BytesIO(pdf.content))
    assert len(reader.pages) > 1
    text = "".join(p.extract_text() for p in reader.pages)
    assert text.count("<review>") == 480
    from pathlib import Path

    Path("/private/tmp/phase2-long-estimate.pdf").write_bytes(pdf.content)
    assert "18.00 USD" in text
