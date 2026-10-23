"""Initial Phase 0 baseline for the DentalVoice API schema.

Revision ID: 20261023_phase0_baseline
Revises: None
Create Date: 2026-10-23
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import Table

from app.db.base import Base

revision = "20261023_phase0_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in reversed(Base.metadata.sorted_tables):
        if not bind.dialect.has_table(bind, table.name):
            table.create(bind=bind)


def downgrade() -> None:
    raise RuntimeError("Downgrades are intentionally disabled for this baseline to protect existing data.")
