# add_partial_reconciliation_status
# Revision ID: 5d6e7f8a9b0c
# Revises: 4c5d6e7f8a9b
# Create Date: 2026-08-21 17:40:00.000000
#
# Why this migration exists:
#   Phase 8 — Finance Truth Layer requires a new reconciliation state (PARTIAL)
#   to handle cases where some, but not all, revenue was recovered.

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5d6e7f8a9b0c'
down_revision: str | None = '4c5d6e7f8a9b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires enum values to be added one at a time.
    # IF NOT EXISTS prevents errors on re-run (idempotent).
    op.execute("ALTER TYPE reconciliationstatus ADD VALUE IF NOT EXISTS 'PARTIAL'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without dropping/recreating the type.
    # Downgrade is intentionally a no-op to avoid destructive schema changes.
    pass
