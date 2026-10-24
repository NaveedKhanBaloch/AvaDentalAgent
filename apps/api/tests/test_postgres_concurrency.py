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
from app.models.models import (
    Tenant,
    Clinic,
    Patient,
    Provider,
    DentalService,
    ClinicBusinessHours,
    Appointment,
)
from app.services.scheduling import save_appointment, SchedulingConflictError


@pytest.fixture
def pg():
    url = os.environ.get("TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_POSTGRES_URL not supplied; PostgreSQL concurrency is not asserted")
    from sqlalchemy.engine import make_url

    if not any(part in (make_url(url).database or "").lower() for part in ("test", "concurrency")):
        pytest.fail(
            "Refusing PostgreSQL tests: database name must identify a disposable test database"
        )
    schema = "phase1_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.connect() as conn:
        if conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('appointments','alembic_version')"
            )
        ).scalar():
            pytest.fail(
                "Refusing PostgreSQL tests with application tables in public; use an empty disposable test DB"
            )
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
            db.add(tenant)
            db.flush()
            clinic = Clinic(tenant_id=tenant.id, name="Test", timezone="UTC")
            db.add(clinic)
            db.flush()
            patient = Patient(
                tenant_id=tenant.id, clinic_id=clinic.id, first_name="Synthetic", last_name="Test"
            )
            providers = [
                Provider(tenant_id=tenant.id, clinic_id=clinic.id, name=f"Test {i}")
                for i in range(2)
            ]
            service = DentalService(
                tenant_id=tenant.id, clinic_id=clinic.id, name="Test", default_duration_minutes=30
            )
            db.add_all([patient, service, *providers])
            db.flush()
            db.add(
                ClinicBusinessHours(
                    clinic_id=clinic.id, weekday=1, opening_time="08:00", closing_time="17:00"
                )
            )
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
    start = datetime(2026, 11, 10, 10, tzinfo=timezone.utc)

    def attempt(i):
        with Session(engine) as db:
            provider_id = providers[0] if shared_provider else providers[i]
            barrier.wait(timeout=10)
            try:
                if through_service:
                    save_appointment(
                        db,
                        db.get(Clinic, clinic_id),
                        db.get(Patient, patient_id),
                        {
                            "provider_id": provider_id,
                            "service_id": service_id,
                            "start_time": start,
                            "end_time": start + timedelta(minutes=30),
                        },
                    )
                else:
                    db.add(
                        Appointment(
                            tenant_id=tenant_id,
                            clinic_id=clinic_id,
                            patient_id=patient_id,
                            provider_id=provider_id,
                            service_id=service_id,
                            start_time=start,
                            end_time=start + timedelta(minutes=30),
                            status="scheduled",
                        )
                    )
                db.commit()
                return "created"
            except (IntegrityError, SchedulingConflictError):
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [0, 1]))
    assert sorted(outcomes) == (
        ["conflict", "created"] if shared_provider else ["created", "created"]
    )
    with Session(engine) as db:
        assert db.query(Appointment).count() == (1 if shared_provider else 2)


@pytest.mark.parametrize("through_service", [True, False])
def test_simultaneous_reschedules(pg, through_service):
    engine, (tenant_id, clinic_id, patient_id, providers, service_id) = pg
    start = datetime(2026, 11, 10, 10, tzinfo=timezone.utc)
    ids = []
    with Session(engine) as db:
        for offset in (0, 1):
            a = Appointment(
                tenant_id=tenant_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                provider_id=providers[0],
                service_id=service_id,
                start_time=start + timedelta(hours=offset),
                end_time=start + timedelta(hours=offset, minutes=30),
                status="scheduled",
            )
            db.add(a)
            db.flush()
            ids.append(a.id)
        db.commit()
    barrier = Barrier(2)

    def move(aid):
        with Session(engine) as db:
            a = db.get(Appointment, aid)
            barrier.wait(timeout=10)
            try:
                if through_service:
                    save_appointment(
                        db,
                        db.get(Clinic, clinic_id),
                        db.get(Patient, patient_id),
                        {
                            "start_time": start + timedelta(hours=2),
                            "end_time": start + timedelta(hours=2, minutes=30),
                        },
                        appointment=a,
                    )
                else:
                    a.start_time, a.end_time = start + timedelta(hours=2), start + timedelta(
                        hours=2, minutes=30
                    )
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
        db.add(
            RetellIntegration(
                tenant_id=tenant_id, clinic_id=clinic_id, agent_id="agent_pg", enabled=True
            )
        )
        db.commit()
    barrier = Barrier(2)

    def event(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return process_webhook(
                db, {"event": "call_ended", "call": {"agent_id": "agent_pg", "call_id": "call_pg"}}
            )["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(event, [0, 1])) == ["accepted", "duplicate"]
    with Session(engine) as db:
        assert db.query(WebhookEvent).count() == 1
        assert db.query(CallLog).count() == 1


def test_concurrent_retell_booking_retry(pg):
    from app.models.models import RetellIntegration, IdempotencyRecord
    from app.api.v1.routes.retell import process_function

    engine, (tenant_id, clinic_id, _, providers, service_id) = pg
    with Session(engine) as db:
        db.add(
            RetellIntegration(
                tenant_id=tenant_id, clinic_id=clinic_id, agent_id="agent_retry", enabled=True
            )
        )
        db.commit()
    payload = {
        "call": {"agent_id": "agent_retry", "call_id": "call_retry"},
        "args": {
            "first_name": "Synthetic",
            "last_name": "Retry",
            "phone": "+12025550123",
            "provider_id": providers[0],
            "service_id": service_id,
            "start_time": "2026-11-10T10:00:00+00:00",
            "confirmed": True,
            "idempotency_key": "same-action",
        },
    }
    barrier = Barrier(2)

    def book(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            return process_function(db, payload, None, "book_appointment", "synthetic-test")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(book, [0, 1]))
    assert first["success"] and first["appointment_id"] == second["appointment_id"]
    with Session(engine) as db:
        assert db.query(Appointment).count() == 1
        assert db.query(IdempotencyRecord).count() == 1


def test_concurrent_estimate_edits(pg):
    from decimal import Decimal
    from fastapi import HTTPException
    from app.models.models import EstimatePolicy, TreatmentEstimate, User
    from app.schemas.estimate import EstimateDraft
    from app.services.estimates import save_draft

    engine, (tenant_id, clinic_id, patient_id, providers, service_id) = pg
    with Session(engine) as db:
        user = User(email="synthetic-policy@example.com", full_name="Test", password_hash="unused")
        db.add(user)
        db.flush()
        db.add(
            EstimatePolicy(
                clinic_id=clinic_id,
                currency="USD",
                minor_units=2,
                tax_rates='{"none":"0"}',
                max_discount_percent=Decimal("0"),
                terms="Synthetic",
                approved_by=user.id,
            )
        )
        db.commit()
        payload = EstimateDraft(
            patient_id=patient_id, issue_date="2026-10-24", items=[{"service_id": service_id}]
        )
        estimate = save_draft(db, db.get(Clinic, clinic_id), payload)
        db.commit()
        eid = estimate.id
    barrier = Barrier(2)

    def edit(_):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            e = db.query(TreatmentEstimate).filter_by(id=eid).with_for_update().first()
            try:
                save_draft(
                    db,
                    db.get(Clinic, clinic_id),
                    EstimateDraft(
                        patient_id=patient_id,
                        issue_date="2026-10-24",
                        expected_revision=1,
                        items=[{"service_id": service_id, "unit_price": "12.34"}],
                    ),
                    e,
                )
                db.commit()
                return "saved"
            except HTTPException as exc:
                db.rollback()
                assert exc.status_code == 409
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, [0, 1])) == ["conflict", "saved"]


def test_duplicate_reminder_preparation(pg):
    from app.models.models import Recall, ReminderPreparation
    from app.services.reminders import prepare_reminders

    engine, (_, clinic_id, patient_id, _, _) = pg
    with Session(engine) as db:
        p = db.get(Patient, patient_id)
        p.email = "synthetic@example.com"
        p.email_consent = True
        db.add(
            Recall(
                tenant_id=p.tenant_id,
                clinic_id=clinic_id,
                patient_id=patient_id,
                recall_type="Approved manual",
                due_date=datetime(2020, 1, 1).date(),
                contact_preference="email",
            )
        )
        db.commit()
    barrier = Barrier(2)

    def prepare(_):
        with Session(engine) as db:
            clinic = db.get(Clinic, clinic_id)
            barrier.wait(timeout=10)
            return prepare_reminders(db, clinic)["processed"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(prepare, [0, 1])) == [0, 1]
    with Session(engine) as db:
        assert db.query(ReminderPreparation).count() == 1


def test_phase2_upgrade_preserves_populated_legacy_columns(pg):
    """Rehearse additive DDL on synthetic Phase 1-shaped tables in an isolated schema."""
    from sqlalchemy import inspect
    from app.models.models import FollowUp

    engine, (tenant_id, clinic_id, patient_id, _, _) = pg
    with Session(engine) as db:
        follow = FollowUp(
            tenant_id=tenant_id,
            clinic_id=clinic_id,
            patient_id=patient_id,
            reason="Synthetic legacy callback",
            priority="normal",
            status="pending",
        )
        db.add(follow)
        db.commit()
        fid = follow.id
    with engine.begin() as conn:
        # This fixture owns only a random disposable schema, never public or production.
        for name in [
            "estimate_acknowledgements",
            "estimate_status_history",
            "estimate_items",
            "estimate_versions",
            "treatment_estimates",
            "estimate_policies",
            "recalls",
            "recall_rules",
            "reminder_preparations",
        ]:
            conn.execute(text(f'DROP TABLE IF EXISTS "{name}" CASCADE'))
        columns = {
            "patients": "date_of_birth status do_not_contact email_consent sms_consent archived_at archived_by updated_at revision",
            "audit_logs": "clinic_id patient_id",
            "follow_ups": "followup_type due_at appointment_id call_id estimate_id notes created_by completed_at completed_by updated_at revision",
        }
        for table, names in columns.items():
            for name in names.split():
                conn.execute(text(f'ALTER TABLE "{table}" DROP COLUMN "{name}" CASCADE'))
        conn.execute(text("DROP INDEX IF EXISTS ix_p2_patient_name"))
        conn.execute(text("UPDATE alembic_version SET version_num='20261023_phase1'"))
        cfg = Config("alembic.ini")
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        patient = conn.execute(
            text(
                "SELECT first_name,status,email_consent,revision,updated_at FROM patients WHERE id=:id"
            ),
            {"id": patient_id},
        ).one()
        assert patient.first_name == "Synthetic" and patient.status == "active"
        assert patient.email_consent is False and patient.revision == 1 and patient.updated_at
        follow = conn.execute(
            text("SELECT reason,followup_type,revision,updated_at FROM follow_ups WHERE id=:id"),
            {"id": fid},
        ).one()
        assert (
            follow.reason == "Synthetic legacy callback"
            and follow.followup_type == "general_callback"
        )
        assert follow.revision == 1 and follow.updated_at
        assert inspect(conn).has_table("estimate_versions")
