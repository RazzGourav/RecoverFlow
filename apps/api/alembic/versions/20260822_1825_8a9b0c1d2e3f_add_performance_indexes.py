"""add_performance_indexes

Revision ID: 8a9b0c1d2e3f
Revises: 5c8babeec60d
Create Date: 2026-08-22 18:25:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8a9b0c1d2e3f'
down_revision: str | None = '5c8babeec60d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE INDEX IF NOT EXISTS ix_payment_events_recovery_case_id ON payment_events (recovery_case_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_recovery_cases_customer_id ON recovery_cases (customer_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_candidate_actions_case_id ON candidate_actions (case_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_funnel_events_session_id ON funnel_events (session_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_payment_events_session_id ON payment_events (session_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_recovery_cases_status ON recovery_cases (status)')

def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_candidate_actions_case_id')
    op.execute('DROP INDEX IF EXISTS ix_recovery_cases_customer_id')
    op.execute('DROP INDEX IF EXISTS ix_payment_events_recovery_case_id')
    op.execute('DROP INDEX IF EXISTS ix_funnel_events_session_id')
    op.execute('DROP INDEX IF EXISTS ix_payment_events_session_id')
    op.execute('DROP INDEX IF EXISTS ix_recovery_cases_status')
