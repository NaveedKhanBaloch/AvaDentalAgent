from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.models import AuditLog, Patient

client = TestClient(app)


def create():
    r = client.post(
        "/api/v1/patients", json={"first_name": "Phase", "last_name": "Two", "phone": "555-0101"}
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_patient_audit_is_committed_and_timeline_bounded():
    p = create()
    with SessionLocal() as db:
        assert db.query(AuditLog).filter_by(patient_id=p["id"]).count() == 1
    r = client.get(f"/api/v1/patients/{p['id']}/timeline?page_size=1").json()
    assert r["total"] == 1 and r["items"][0]["event_type"] == "patient.registered"
    assert client.get("/api/v1/patients?page_size=1").json()["total"] == 4


def test_revision_archive_restore_and_clear_optional():
    p = create()
    path = f"/api/v1/patients/{p['id']}"
    r = client.patch(path, json={"expected_revision": 1, "phone": None})
    assert r.status_code == 200 and r.json()["phone"] is None
    assert client.patch(path, json={"expected_revision": 1, "notes": "stale"}).status_code == 409
    archived = client.post(
        path + "/archive", json={"expected_revision": 2, "confirmed": True}
    ).json()
    assert archived["status"] == "archived"
    assert (
        client.post(path + "/restore", json={"expected_revision": 3, "confirmed": True}).json()[
            "status"
        ]
        == "active"
    )


def test_invalid_birth_date_and_related_delete():
    assert (
        client.post(
            "/api/v1/patients",
            json={"first_name": "A", "last_name": "B", "date_of_birth": "2999-01-01"},
        ).status_code
        == 422
    )
    p = client.get("/api/v1/patients").json()["items"][0]
    assert client.delete("/api/v1/patients/" + p["id"]).status_code == 409


def test_patient_write_and_audit_rollback_together(monkeypatch):
    import app.api.v1.routes.patients as routes

    with SessionLocal() as db:
        before = db.query(Patient).count()

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr(routes, "event", fail)
    with TestClient(app, raise_server_exceptions=False) as c:
        assert (
            c.post(
                "/api/v1/patients", json={"first_name": "Atomic", "last_name": "Test"}
            ).status_code
            == 500
        )
    with SessionLocal() as db:
        assert db.query(Patient).count() == before
