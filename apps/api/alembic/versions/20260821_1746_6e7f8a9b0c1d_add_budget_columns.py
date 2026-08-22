# add_budget_columns
# Revision ID: 6e7f8a9b0c1d
# Revises: 5d6e7f8a9b0c
# Create Date: 2026-08-21 17:46:00.000000
#
# Why this migration exists:
#   Phase 8.5 — Budget Optimizer requires tracking max spend limit on Policies
#   and execution cost on CandidateActions to support greedy-ratio knapsack allocation.

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6e7f8a9b0c1d'
down_revision: str | None = '5d6e7f8a9b0c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('policies', sa.Column('max_recovery_spend_paise', sa.BigInteger(), nullable=True))
    op.add_column('candidate_actions', sa.Column('action_cost_paise', sa.BigInteger(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('candidate_actions', 'action_cost_paise')
    op.drop_column('policies', 'max_recovery_spend_paise')
