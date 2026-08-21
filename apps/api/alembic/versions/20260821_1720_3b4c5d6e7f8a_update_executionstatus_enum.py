# update_executionstatus_enum_values
# Revision ID: 3b4c5d6e7f8a
# Revises: 2a3b4c5d6e7f
# Create Date: 2026-08-21 17:20:00.000000
#
# Why this migration exists:
#   Phase 7 — Action Layer requires explicit execution state transitions.
#   Added new states: EXECUTED, VERIFIED, TIMED_OUT, EXCEPTION.

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3b4c5d6e7f8a'
down_revision: str | None = '2a3b4c5d6e7f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires enum values to be added one at a time.
    # IF NOT EXISTS prevents errors on re-run (idempotent).
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'EXECUTED'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'VERIFIED'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'TIMED_OUT'")
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'EXCEPTION'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without dropping/recreating the type.
    # Downgrade is intentionally a no-op to avoid destructive schema changes.
    pass
