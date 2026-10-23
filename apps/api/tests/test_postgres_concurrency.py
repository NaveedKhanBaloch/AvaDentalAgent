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
    schema = "phase1_test_" + uuid.uuid4().hex
    admin = create_engine(url)
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
