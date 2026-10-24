"""Add patient administration and attributable audit context without deleting data."""

from alembic import op
import sqlalchemy as sa

revision = "20261024_phase2a"
down_revision = "20261023_phase1"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    additions = {
        "patients": [
            sa.Column("date_of_birth", sa.Date()),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("do_not_contact", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("email_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("sms_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("archived_at", sa.DateTime(timezone=True)),
            sa.Column("archived_by", sa.String(36)),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        ],
        "audit_logs": [
            sa.Column("clinic_id", sa.String(36), sa.ForeignKey("clinics.id")),
            sa.Column("patient_id", sa.String(36)),
        ],
    }
    for table, columns in additions.items():
        known = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        for col in columns:
            if col.name not in known:
                op.add_column(table, col)
    op.execute("UPDATE patients SET updated_at=created_at WHERE updated_at IS NULL")
    for table, name, columns in [
        ("patients", "ix_p2_patient_clinic_status", ["clinic_id", "status", "created_at"]),
        ("patients", "ix_p2_patient_name", ["clinic_id", "last_name", "first_name"]),
        ("audit_logs", "ix_p2_patient_events", ["clinic_id", "patient_id", "timestamp"]),
    ]:
        op.create_index(name, table, columns)


def downgrade():
    raise RuntimeError("Use a reviewed forward migration; patient history must be retained")
