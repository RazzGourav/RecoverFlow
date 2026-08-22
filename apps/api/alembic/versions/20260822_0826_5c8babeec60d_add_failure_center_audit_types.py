# Add failure center audit types
# Revision ID: 5c8babeec60d
# Revises: 7f8a9b0c1d2e
# Create Date: 2026-08-22 08:26:06.704169

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5c8babeec60d'
down_revision: str | None = '7f8a9b0c1d2e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'WEBHOOK_DUPLICATE_DROPPED'")
        op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'VALIDATION_BLOCKED'")
        op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'ACTION_TIMEOUT'")
        op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'RECONCILIATION_EXCEPTION'")
        op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'BUDGET_EXHAUSTED'")


def downgrade() -> None:
    pass
