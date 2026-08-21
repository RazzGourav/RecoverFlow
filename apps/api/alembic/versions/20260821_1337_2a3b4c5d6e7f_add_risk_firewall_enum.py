# add_risk_firewall_enum_values
# Revision ID: 2a3b4c5d6e7f
# Revises: 151b631eba3d
# Create Date: 2026-08-21 13:37:00.000000
#
# Why this migration exists:
#   Phase 6 — Risk Firewall adds two new AuditEventType values:
#     RISK_FIREWALL_EVALUATED — logged when firewall runs but does not block
#     RISK_FIREWALL_BLOCKED   — logged when firewall produces a BLOCK outcome
#
#   Reason codes for these events always start with "RISK_" prefix, making them
#   distinguishable from Policy Engine events ("POLICY_" prefix) in audit queries.

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: str | None = '151b631eba3d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL requires enum values to be added one at a time.
    # IF NOT EXISTS prevents errors on re-run (idempotent).
    op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'RISK_FIREWALL_EVALUATED'")
    op.execute("ALTER TYPE auditeventtype ADD VALUE IF NOT EXISTS 'RISK_FIREWALL_BLOCKED'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without dropping/recreating the type.
    # Downgrade is intentionally a no-op to avoid destructive schema changes.
    # If rollback is needed, the enum values are harmlessly unused after downgrade.
    pass
