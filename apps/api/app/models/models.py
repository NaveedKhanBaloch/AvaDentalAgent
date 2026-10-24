from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Date,
    Numeric,
    UniqueConstraint,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    subscription_plan: Mapped[str] = mapped_column(String(100), default="starter")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, default=None)
    city: Mapped[str | None] = mapped_column(String(120), default=None)
    state: Mapped[str | None] = mapped_column(String(120), default=None)
    country: Mapped[str | None] = mapped_column(String(120), default="US")
    timezone: Mapped[str | None] = mapped_column(String(64), default="America/New_York")
    phone: Mapped[str | None] = mapped_column(String(30), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(50), default="active")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clinics.id"), default=None
    )
    role: Mapped[str] = mapped_column(String(80), default="receptionist")
    status: Mapped[str] = mapped_column(String(50), default="active")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), default=None)
    specialty: Mapped[str | None] = mapped_column(String(120), default=None)
    active_status: Mapped[bool] = mapped_column(Boolean, default=True)


class DentalService(Base):
    __tablename__ = "dental_services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    default_duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    indicative_price: Mapped[float] = mapped_column(default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    active_status: Mapped[bool] = mapped_column(Boolean, default=True)


class Patient(Base):
    __tablename__ = "patients"
    date_of_birth: Mapped[date | None] = mapped_column(Date, default=None)
    status: Mapped[str] = mapped_column(
        String(30), default="active", server_default="active", index=True
    )
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    email_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sms_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    archived_by: Mapped[str | None] = mapped_column(String(36), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), default=None)
    email: Mapped[str | None] = mapped_column(String(255), default=None)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(30), default="phone")
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("providers.id"), default=None
    )
    service_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("dental_services.id"), default=None
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    source: Mapped[str] = mapped_column(String(50), default="dashboard")
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class InsuranceProfile(Base):
    __tablename__ = "insurance_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    carrier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_number: Mapped[str | None] = mapped_column(String(120), default=None)
    group_number: Mapped[str | None] = mapped_column(String(120), default=None)
    member_name: Mapped[str | None] = mapped_column(String(255), default=None)
    subscriber_dob: Mapped[str | None] = mapped_column(String(30), default=None)
    relationship_to_patient: Mapped[str | None] = mapped_column(String(80), default=None)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ClinicBusinessHours(Base):
    __tablename__ = "clinic_business_hours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    opening_time: Mapped[str] = mapped_column(String(20), nullable=False)
    closing_time: Mapped[str] = mapped_column(String(20), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class ScheduleException(Base):
    __tablename__ = "schedule_exceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    provider_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("providers.id"), default=None
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), default=None)
    exception_type: Mapped[str] = mapped_column(String(60), default="closure")


class RetellIntegration(Base):
    __tablename__ = "retell_integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(255), default=None)
    phone_number: Mapped[str | None] = mapped_column(String(50), default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    configuration: Mapped[str | None] = mapped_column(Text, default=None)


class CallLog(Base):
    __tablename__ = "call_logs"
    __table_args__ = (
        UniqueConstraint("clinic_id", "external_call_id", name="uq_call_clinic_external"),
    )
    patient_id: Mapped[str | None] = mapped_column(ForeignKey("patients.id"), default=None)
    appointment_id: Mapped[str | None] = mapped_column(ForeignKey("appointments.id"), default=None)
    escalation_status: Mapped[str | None] = mapped_column(String(40), default=None)
    event_rank: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    external_call_id: Mapped[str | None] = mapped_column(String(255), default=None)
    caller_number: Mapped[str | None] = mapped_column(String(30), default=None)
    direction: Mapped[str] = mapped_column(String(20), default="inbound")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[str] = mapped_column(String(50), default="completed")
    outcome: Mapped[str | None] = mapped_column(String(80), default=None)
    transcript_reference: Mapped[str | None] = mapped_column(String(255), default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FollowUp(Base):
    __tablename__ = "follow_ups"
    followup_type: Mapped[str] = mapped_column(
        String(80), default="general_callback", server_default="general_callback"
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, index=True
    )
    appointment_id: Mapped[str | None] = mapped_column(ForeignKey("appointments.id"), default=None)
    call_id: Mapped[str | None] = mapped_column(ForeignKey("call_logs.id"), default=None)
    estimate_id: Mapped[str | None] = mapped_column(
        ForeignKey("treatment_estimates.id"), default=None
    )
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[str | None] = mapped_column(String(36), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_by: Mapped[str | None] = mapped_column(String(36), default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    clinic_id: Mapped[str] = mapped_column(String(36), ForeignKey("clinics.id"), nullable=False)
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("patients.id"), default=None
    )
    contact_name: Mapped[str | None] = mapped_column(String(255), default=None)
    contact_phone: Mapped[str | None] = mapped_column(String(30), default=None)
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    priority: Mapped[str] = mapped_column(String(30), default="normal")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    clinic_id: Mapped[str | None] = mapped_column(
        ForeignKey("clinics.id"), default=None, index=True
    )
    patient_id: Mapped[str | None] = mapped_column(String(36), default=None, index=True)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), default="user")
    actor_id: Mapped[str | None] = mapped_column(String(36), default=None)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), default=None)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    audit_metadata: Mapped[str | None] = mapped_column(Text, default=None)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tenants.id"), default=None
    )
    provider: Mapped[str] = mapped_column(String(80), default="retell")
    external_event_id: Mapped[str | None] = mapped_column(String(255), default=None)
    payload_reference: Mapped[str | None] = mapped_column(Text, default=None)
    processing_status: Mapped[str] = mapped_column(String(40), default="received")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False)
    operation: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    request_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    response_reference: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProviderWorkingHours(Base):
    __tablename__ = "provider_working_hours"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    weekday: Mapped[int] = mapped_column(Integer)
    opening_time: Mapped[str] = mapped_column(String(20))
    closing_time: Mapped[str] = mapped_column(String(20))


class ProviderService(Base):
    __tablename__ = "provider_services"
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), primary_key=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("dental_services.id"), primary_key=True)


class Recall(Base):
    __tablename__ = "recalls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    recall_rule_id: Mapped[str | None] = mapped_column(ForeignKey("recall_rules.id"), default=None)
    recall_type: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(30), default="due")
    assigned_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), default=None)
    origin_appointment_id: Mapped[str | None] = mapped_column(
        ForeignKey("appointments.id"), default=None
    )
    appointment_id: Mapped[str | None] = mapped_column(ForeignKey("appointments.id"), default=None)
    contact_preference: Mapped[str] = mapped_column(String(30), default="phone")
    last_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completion_reason: Mapped[str | None] = mapped_column(Text, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_by: Mapped[str | None] = mapped_column(String(36), default=None)
    completed_by: Mapped[str | None] = mapped_column(String(36), default=None)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ReminderPreparation(Base):
    __tablename__ = "reminder_preparations"
    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "entity_type",
            "entity_id",
            "revision",
            "channel",
            name="uq_preparation_entity_revision_channel",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(36))
    revision: Mapped[int] = mapped_column(Integer)
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str | None] = mapped_column(String(200), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecallRule(Base):
    __tablename__ = "recall_rules"
    __table_args__ = (UniqueConstraint("clinic_id", "name", name="uq_recall_rule_name"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    interval_days: Mapped[int] = mapped_column(Integer)
    approved_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EstimatePolicy(Base):
    __tablename__ = "estimate_policies"
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(10))
    minor_units: Mapped[int] = mapped_column(Integer)
    tax_rates: Mapped[str] = mapped_column(Text)
    max_discount_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    terms: Mapped[str] = mapped_column(Text)
    validity_days: Mapped[int | None] = mapped_column(Integer, default=None)
    approved_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revision: Mapped[int] = mapped_column(Integer, default=1)


class TreatmentEstimate(Base):
    __tablename__ = "treatment_estimates"
    __table_args__ = (UniqueConstraint("clinic_id", "number", name="uq_estimate_clinic_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    clinic_id: Mapped[str] = mapped_column(ForeignKey("clinics.id"), index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    number: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[str | None] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class EstimateVersion(Base):
    __tablename__ = "estimate_versions"
    __table_args__ = (UniqueConstraint("estimate_id", "version", name="uq_estimate_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    estimate_id: Mapped[str] = mapped_column(ForeignKey("treatment_estimates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    currency: Mapped[str] = mapped_column(String(10))
    minor_units: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    discount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    issue_date: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date, default=None)
    terms: Mapped[str] = mapped_column(Text)
    policy_snapshot: Mapped[str] = mapped_column(Text)
    clinic_snapshot: Mapped[str] = mapped_column(Text)
    patient_snapshot: Mapped[str] = mapped_column(Text)
    revision_reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_by: Mapped[str | None] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EstimateItem(Base):
    __tablename__ = "estimate_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(ForeignKey("estimate_versions.id"), index=True)
    service_id: Mapped[str] = mapped_column(ForeignKey("dental_services.id"))
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    tax_label: Mapped[str] = mapped_column(String(100))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    discount: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    tax: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    position: Mapped[int] = mapped_column(Integer)


class EstimateStatusHistory(Base):
    __tablename__ = "estimate_status_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    estimate_id: Mapped[str] = mapped_column(ForeignKey("treatment_estimates.id"), index=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("estimate_versions.id"))
    previous_status: Mapped[str | None] = mapped_column(String(30), default=None)
    status: Mapped[str] = mapped_column(String(30))
    actor_id: Mapped[str | None] = mapped_column(String(36), default=None)
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EstimateAcknowledgement(Base):
    __tablename__ = "estimate_acknowledgements"
    __table_args__ = (UniqueConstraint("version_id", name="uq_acknowledgement_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_id: Mapped[str] = mapped_column(ForeignKey("estimate_versions.id"))
    decision: Mapped[str] = mapped_column(String(30))
    acknowledged_by_name: Mapped[str] = mapped_column(String(255))
    method: Mapped[str] = mapped_column(String(100))
    recorded_by: Mapped[str | None] = mapped_column(String(36), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
