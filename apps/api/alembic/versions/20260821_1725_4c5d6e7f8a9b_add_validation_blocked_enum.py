# add_validation_blocked_enum
# Revision ID: 4c5d6e7f8a9b
# Revises: 3b4c5d6e7f8a
# Create Date: 2026-08-21 17:25:00.000000
#
# Why this migration exists:
#   Phase 7.5 — Validation Layer requires a new execution state to represent
#   actions that were blocked right before execution because the live provider
#   state was incompatible with the recommended action.

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4c5d6e7f8a9b'
down_revision: str | None = '3b4c5d6e7f8a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires enum values to be added one at a time.
    # IF NOT EXISTS prevents errors on re-run (idempotent).
    op.execute("ALTER TYPE executionstatus ADD VALUE IF NOT EXISTS 'VALIDATION_BLOCKED'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without dropping/recreating the type.
    # Downgrade is intentionally a no-op to avoid destructive schema changes.
    pass
