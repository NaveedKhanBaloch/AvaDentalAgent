"""Run only against an explicitly supplied disposable PostgreSQL test database."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timedelta, timezone
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.models import Tenant, Clinic, Patient, Provider, DentalService, ClinicBusinessHours, Appointment
from app.services.scheduling import save_appointment, SchedulingConflictError

@pytest.fixture
def pg():
    url = os.environ.get("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL not supplied; PostgreSQL concurrency is not asserted")
    from sqlalchemy.engine import make_url
    if not any(part in (make_url(url).database or "").lower() for part in ("test", "concurrency")):
        pytest.fail("Refusing PostgreSQL tests: database name must identify a disposable test database")
    schema = "phase1_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.connect() as conn:
        if conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('appointments','alembic_version')")).scalar():
            pytest.fail("Refusing PostgreSQL tests with application tables in public; use an empty disposable test DB")
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema},public"})
    try:
        with engine.begin() as conn:
            cfg = Config("alembic.ini")
            cfg.attributes["connection"] = conn
            command.upgrade(cfg, "head")
        with Session(engine) as db:
            tenant = Tenant(name="Concurrency Test", slug=uuid.uuid4().hex)
            db.add(tenant); db.flush()
            clinic = Clinic(tenant_id=tenant.id, name="Test", timezone="UTC")
            db.add(clinic); db.flush()
            patient = Patient(tenant_id=tenant.id, clinic_id=clinic.id, first_name="Synthetic", last_name="Test")
            providers = [Provider(tenant_id=tenant.id, clinic_id=clinic.id, name=f"Test {i}") for i in range(2)]
            service = DentalService(tenant_id=tenant.id, clinic_id=clinic.id, name="Test", default_duration_minutes=30)
            db.add_all([patient, service, *providers]); db.flush()
            db.add(ClinicBusinessHours(clinic_id=clinic.id, weekday=1, opening_time="08:00", closing_time="17:00"))
            ids = (tenant.id, clinic.id, patient.id, [p.id for p in providers], service.id)
            db.commit()
        yield engine, ids
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()

@pytest.mark.parametrize("shared_provider", [True, False])
@pytest.mark.parametrize("through_service", [True, False])
def test_simultaneous_booking(pg, shared_provider, through_service):
    engine, (tenant_id, clinic_id, patient_id, providers, service_id) = pg
    barrier = Barrier(2)
    start = datetime(2026,11,10,10,tzinfo=timezone.utc)
    def attempt(i):
        with Session(engine) as db:
            provider_id = providers[0] if shared_provider else providers[i]
            barrier.wait(timeout=10)
            try:
                if through_service:
                    save_appointment(db, db.get(Clinic, clinic_id), db.get(Patient, patient_id),
                        {"provider_id": provider_id, "service_id": service_id, "start_time": start,
                         "end_time": start + timedelta(minutes=30)})
                else:
                    db.add(Appointment(tenant_id=tenant_id, clinic_id=clinic_id, patient_id=patient_id,
                        provider_id=provider_id, service_id=service_id, start_time=start,
                        end_time=start + timedelta(minutes=30), status="scheduled"))
                db.commit()
                return "created"
            except (IntegrityError, SchedulingConflictError):
                db.rollback()
                return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [0, 1]))
    assert sorted(outcomes) == (["conflict", "created"] if shared_provider else ["created", "created"])
    with Session(engine) as db:
        assert db.query(Appointment).count() == (1 if shared_provider else 2)


@pytest.mark.parametrize("through_service", [True, False])
def test_simultaneous_reschedules(pg, through_service):
    engine, (tenant_id, clinic_id, patient_id, providers, service_id) = pg
    start = datetime(2026,11,10,10,tzinfo=timezone.utc)
    ids = []
    with Session(engine) as db:
        for offset in (0, 1):
            a = Appointment(tenant_id=tenant_id, clinic_id=clinic_id, patient_id=patient_id,
                provider_id=providers[0], service_id=service_id, start_time=start+timedelta(hours=offset),
                end_time=start+timedelta(hours=offset, minutes=30), status="scheduled")
            db.add(a); db.flush(); ids.append(a.id)
        db.commit()
    barrier = Barrier(2)
    def move(aid):
        with Session(engine) as db:
            a = db.get(Appointment, aid)
            barrier.wait(timeout=10)
            try:
                if through_service:
                    save_appointment(db, db.get(Clinic, clinic_id), db.get(Patient, patient_id),
                        {"start_time": start+timedelta(hours=2), "end_time": start+timedelta(hours=2,minutes=30)}, appointment=a)
                else:
                    a.start_time, a.end_time = start+timedelta(hours=2), start+timedelta(hours=2,minutes=30)
                db.commit()
                return "moved"
            except (IntegrityError, SchedulingConflictError):
                db.rollback()
                return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(move, ids)) == ["conflict", "moved"]


def test_concurrent_duplicate_webhooks(pg):
    from app.models.models import RetellIntegration, WebhookEvent, CallLog
    from app.api.v1.routes.retell import process_webhook
    engine, (tenant_id, clinic_id, _, _, _) = pg
    with Session(engine) as db:
        db.add(RetellIntegration(tenant_id=tenant_id, clinic_id=clinic_id, agent_id="agent_pg", enabled=True))
        db.commit()
    barrier = Barrier(2)
    def event(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return process_webhook(db, {"event": "call_ended", "call": {"agent_id": "agent_pg", "call_id": "call_pg"}})["status"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(event, [0,1])) == ["accepted", "duplicate"]
    with Session(engine) as db:
        assert db.query(WebhookEvent).count() == 1
        assert db.query(CallLog).count() == 1


def test_concurrent_retell_booking_retry(pg):
    from app.models.models import RetellIntegration, IdempotencyRecord
    from app.api.v1.routes.retell import process_function
    engine, (tenant_id, clinic_id, _, providers, service_id) = pg
    with Session(engine) as db:
        db.add(RetellIntegration(tenant_id=tenant_id, clinic_id=clinic_id, agent_id="agent_retry", enabled=True))
        db.commit()
    payload = {"call": {"agent_id": "agent_retry", "call_id": "call_retry"}, "args": {
        "first_name": "Synthetic", "last_name": "Retry", "phone": "+12025550123", "provider_id": providers[0],
        "service_id": service_id, "start_time": "2026-11-10T10:00:00+00:00", "confirmed": True, "idempotency_key": "same-action"}}
    barrier = Barrier(2)
    def book(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return process_function(db, payload, None, "book_appointment", "synthetic-test")
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(book, [0,1]))
    assert first["success"] and first["appointment_id"] == second["appointment_id"]
    with Session(engine) as db:
        assert db.query(Appointment).count() == 1
        assert db.query(IdempotencyRecord).count() == 1
