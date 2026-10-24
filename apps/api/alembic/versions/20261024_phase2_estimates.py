"""Versioned decimal-safe treatment estimates and administrative acknowledgements."""

from alembic import op
import sqlalchemy as sa

revision = "20261024_phase2c"
down_revision = "20261024_phase2b"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("estimate_policies"):
        op.create_table(
            "estimate_policies",
            sa.Column(
                "clinic_id",
                sa.String(length=36),
                sa.ForeignKey("clinics.id"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column("currency", sa.String(length=10), nullable=False),
            sa.Column("minor_units", sa.Integer(), nullable=False),
            sa.Column("tax_rates", sa.Text(), nullable=False),
            sa.Column("max_discount_percent", sa.Numeric(precision=7, scale=4), nullable=False),
            sa.Column("terms", sa.Text(), nullable=False),
            sa.Column("validity_days", sa.Integer(), nullable=True),
            sa.Column(
                "approved_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
            ),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
        )
    if not sa.inspect(bind).has_table("treatment_estimates"):
        op.create_table(
            "treatment_estimates",
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
            sa.Column("number", sa.String(length=60), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("current_version", sa.Integer(), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("clinic_id", "number", name="uq_estimate_clinic_number"),
        )
        op.create_index("ix_treatment_estimates_patient_id", "treatment_estimates", ["patient_id"])
        op.create_index("ix_treatment_estimates_clinic_id", "treatment_estimates", ["clinic_id"])
        op.create_index("ix_treatment_estimates_status", "treatment_estimates", ["status"])
    if not sa.inspect(bind).has_table("estimate_versions"):
        op.create_table(
            "estimate_versions",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "estimate_id",
                sa.String(length=36),
                sa.ForeignKey("treatment_estimates.id"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("currency", sa.String(length=10), nullable=False),
            sa.Column("minor_units", sa.Integer(), nullable=False),
            sa.Column("subtotal", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("discount", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("tax", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("total", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("issue_date", sa.Date(), nullable=False),
            sa.Column("valid_until", sa.Date(), nullable=True),
            sa.Column("terms", sa.Text(), nullable=False),
            sa.Column("policy_snapshot", sa.Text(), nullable=False),
            sa.Column("clinic_snapshot", sa.Text(), nullable=False),
            sa.Column("patient_snapshot", sa.Text(), nullable=False),
            sa.Column("revision_reason", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("estimate_id", "version", name="uq_estimate_version"),
        )
        op.create_index("ix_estimate_versions_estimate_id", "estimate_versions", ["estimate_id"])
    if not sa.inspect(bind).has_table("estimate_items"):
        op.create_table(
            "estimate_items",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "version_id",
                sa.String(length=36),
                sa.ForeignKey("estimate_versions.id"),
                nullable=False,
            ),
            sa.Column(
                "service_id",
                sa.String(length=36),
                sa.ForeignKey("dental_services.id"),
                nullable=False,
            ),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=False),
            sa.Column("unit_price", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("discount_percent", sa.Numeric(precision=7, scale=4), nullable=False),
            sa.Column("tax_label", sa.String(length=100), nullable=False),
            sa.Column("tax_rate", sa.Numeric(precision=7, scale=4), nullable=False),
            sa.Column("subtotal", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("discount", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("tax", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("total", sa.Numeric(precision=18, scale=4), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
        )
        op.create_index("ix_estimate_items_version_id", "estimate_items", ["version_id"])
    if not sa.inspect(bind).has_table("estimate_status_history"):
        op.create_table(
            "estimate_status_history",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "estimate_id",
                sa.String(length=36),
                sa.ForeignKey("treatment_estimates.id"),
                nullable=False,
            ),
            sa.Column(
                "version_id",
                sa.String(length=36),
                sa.ForeignKey("estimate_versions.id"),
                nullable=False,
            ),
            sa.Column("previous_status", sa.String(length=30), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_estimate_status_history_estimate_id", "estimate_status_history", ["estimate_id"]
        )
    if not sa.inspect(bind).has_table("estimate_acknowledgements"):
        op.create_table(
            "estimate_acknowledgements",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "version_id",
                sa.String(length=36),
                sa.ForeignKey("estimate_versions.id"),
                nullable=False,
            ),
            sa.Column("decision", sa.String(length=30), nullable=False),
            sa.Column("acknowledged_by_name", sa.String(length=255), nullable=False),
            sa.Column("method", sa.String(length=100), nullable=False),
            sa.Column("recorded_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("version_id", name="uq_acknowledgement_version"),
        )

    if not any(
        fk["constrained_columns"] == ["estimate_id"]
        for fk in sa.inspect(bind).get_foreign_keys("follow_ups")
    ):
        op.create_foreign_key(
            "fk_followup_estimate", "follow_ups", "treatment_estimates", ["estimate_id"], ["id"]
        )


def downgrade():
    raise RuntimeError("Estimate history is retained; use a reviewed forward migration")
