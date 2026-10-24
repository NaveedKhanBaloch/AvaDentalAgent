"""Extend the existing follow-up queue and add recalls and sandbox preparation."""

from alembic import op
import sqlalchemy as sa

revision = "20261024_phase2b"
down_revision = "20261024_phase2a"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    known = {c["name"] for c in sa.inspect(bind).get_columns("follow_ups")}
    if "followup_type" not in known:
        op.add_column(
            "follow_ups",
            sa.Column(
                "followup_type",
                sa.String(length=80),
                nullable=False,
                server_default="general_callback",
            ),
        )
    if "due_at" not in known:
        op.add_column("follow_ups", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    if "appointment_id" not in known:
        op.add_column(
            "follow_ups",
            sa.Column(
                "appointment_id",
                sa.String(length=36),
                sa.ForeignKey("appointments.id"),
                nullable=True,
            ),
        )
    if "call_id" not in known:
        op.add_column(
            "follow_ups",
            sa.Column(
                "call_id", sa.String(length=36), sa.ForeignKey("call_logs.id"), nullable=True
            ),
        )
    if "estimate_id" not in known:
        op.add_column("follow_ups", sa.Column("estimate_id", sa.String(length=36), nullable=True))
    if "notes" not in known:
        op.add_column("follow_ups", sa.Column("notes", sa.Text(), nullable=True))
    if "created_by" not in known:
        op.add_column("follow_ups", sa.Column("created_by", sa.String(length=36), nullable=True))
    if "completed_at" not in known:
        op.add_column(
            "follow_ups", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
        )
    if "completed_by" not in known:
        op.add_column("follow_ups", sa.Column("completed_by", sa.String(length=36), nullable=True))
    if "updated_at" not in known:
        op.add_column(
            "follow_ups",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
    if "revision" not in known:
        op.add_column(
            "follow_ups",
            sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )
    if not sa.inspect(bind).has_table("recall_rules"):
        op.create_table(
            "recall_rules",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "clinic_id", sa.String(length=36), sa.ForeignKey("clinics.id"), nullable=False
            ),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("interval_days", sa.Integer(), nullable=False),
            sa.Column(
                "approved_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("clinic_id", "name", name="uq_recall_rule_name"),
        )
        op.create_index("ix_recall_rules_clinic_id", "recall_rules", ["clinic_id"])
    if not sa.inspect(bind).has_table("recalls"):
        op.create_table(
            "recalls",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id"), nullable=False
            ),
            sa.Column(
                "clinic_id", sa.String(length=36), sa.ForeignKey("clinics.id"), nullable=False
            ),
            sa.Column(
                "patient_id", sa.String(length=36), sa.ForeignKey("patients.id"), nullable=False
            ),
            sa.Column(
                "recall_rule_id",
                sa.String(length=36),
                sa.ForeignKey("recall_rules.id"),
                nullable=True,
            ),
            sa.Column("recall_type", sa.String(length=80), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column(
                "assigned_user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True
            ),
            sa.Column(
                "origin_appointment_id",
                sa.String(length=36),
                sa.ForeignKey("appointments.id"),
                nullable=True,
            ),
            sa.Column(
                "appointment_id",
                sa.String(length=36),
                sa.ForeignKey("appointments.id"),
                nullable=True,
            ),
            sa.Column("contact_preference", sa.String(length=30), nullable=False),
            sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completion_reason", sa.Text(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("completed_by", sa.String(length=36), nullable=True),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index("ix_recalls_patient_id", "recalls", ["patient_id"])
        op.create_index("ix_recalls_due_date", "recalls", ["due_date"])
        op.create_index("ix_recalls_clinic_id", "recalls", ["clinic_id"])
    if not sa.inspect(bind).has_table("reminder_preparations"):
        op.create_table(
            "reminder_preparations",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "clinic_id", sa.String(length=36), sa.ForeignKey("clinics.id"), nullable=False
            ),
            sa.Column("entity_type", sa.String(length=30), nullable=False),
            sa.Column("entity_id", sa.String(length=36), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("channel", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.String(length=200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "clinic_id",
                "entity_type",
                "entity_id",
                "revision",
                "channel",
                name="uq_preparation_entity_revision_channel",
            ),
        )
        op.create_index(
            "ix_reminder_preparations_clinic_id", "reminder_preparations", ["clinic_id"]
        )

    known_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("follow_ups")}
    if "ix_follow_ups_due_at" not in known_indexes:
        op.create_index("ix_follow_ups_due_at", "follow_ups", ["due_at"])
    if "ix_p2_followup_queue" not in known_indexes:
        op.create_index("ix_p2_followup_queue", "follow_ups", ["clinic_id", "status", "due_at"])


def downgrade():
    raise RuntimeError("Reviewed forward migrations only; operational history is retained")
