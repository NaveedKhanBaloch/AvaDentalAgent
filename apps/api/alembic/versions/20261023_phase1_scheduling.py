"""Add scheduling configuration, call attribution and database overlap protection."""
from alembic import op
import sqlalchemy as sa

revision = "20261023_phase1"
down_revision = "20261023_phase0_baseline"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Baseline imports current metadata; guard additions for fresh installs.
    if not inspector.has_table("provider_working_hours"):
        op.create_table("provider_working_hours", sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("provider_id", sa.String(36), sa.ForeignKey("providers.id"), nullable=False),
            sa.Column("weekday", sa.Integer(), nullable=False), sa.Column("opening_time", sa.String(20), nullable=False),
            sa.Column("closing_time", sa.String(20), nullable=False))
        op.create_index("ix_provider_working_hours_provider_id", "provider_working_hours", ["provider_id"])
    if not inspector.has_table("provider_services"):
        op.create_table("provider_services", sa.Column("provider_id", sa.String(36), sa.ForeignKey("providers.id"), primary_key=True),
            sa.Column("service_id", sa.String(36), sa.ForeignKey("dental_services.id"), primary_key=True))
    columns = {c["name"] for c in inspector.get_columns("call_logs")}
    additions = [sa.Column("patient_id", sa.String(36), nullable=True), sa.Column("appointment_id", sa.String(36), nullable=True),
        sa.Column("escalation_status", sa.String(40), nullable=True), sa.Column("event_rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True)]
    for column in additions:
        if column.name not in columns:
            op.add_column("call_logs", column)
    unique = {c["name"] for c in inspector.get_unique_constraints("call_logs")}
    if "uq_call_clinic_external" not in unique:
        op.create_index("uq_call_clinic_external", "call_logs", ["clinic_id", "external_call_id"], unique=True)
    op.create_index("ix_appointment_provider_interval", "appointments", ["clinic_id", "provider_id", "start_time", "end_time"])
    op.create_index("ix_webhook_provider_event", "webhook_events", ["provider", "external_event_id"], unique=True)
    if bind.dialect.name == "postgresql":
        # Fails safely on legacy overlaps: operator must review; no data is changed/deleted.
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        op.execute("ALTER TABLE appointments ADD CONSTRAINT appointment_positive_range CHECK (end_time > start_time)")
        op.execute("""ALTER TABLE appointments ADD CONSTRAINT appointment_provider_no_overlap
          EXCLUDE USING gist (clinic_id WITH =, provider_id WITH =,
            tstzrange(start_time, end_time, '[)') WITH &&) WHERE (status <> 'cancelled')""")


def downgrade():
    raise RuntimeError("Phase 1 downgrade requires a reviewed forward migration; data is preserved.")
