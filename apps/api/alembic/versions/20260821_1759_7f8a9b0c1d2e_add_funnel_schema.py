# add_funnel_schema
# Revision ID: 7f8a9b0c1d2e
# Revises: 6e7f8a9b0c1d
# Create Date: 2026-08-21 17:59:00.000000
#
# Why this migration exists:
#   Phase 9 — Funnel Infrastructure adds top-of-funnel tracking tables (sessions, funnel_events)
#   and links them to payment_events to connect the synthetic funnel with real recovery data.

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7f8a9b0c1d2e'
down_revision: str | None = '6e7f8a9b0c1d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create Enum
    op.execute("CREATE TYPE funneleventtype AS ENUM ('SITE_VISIT', 'PRODUCT_VIEW', 'ADD_TO_CART', 'CHECKOUT_STARTED', 'PAYMENT_ATTEMPTED')")

    # 2. Create Sessions Table
    op.create_table('sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('customer_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_customer_id'), 'sessions', ['customer_id'], unique=False)

    # 3. Create FunnelEvents Table
    op.create_table('funnel_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('event_type', postgresql.ENUM('SITE_VISIT', 'PRODUCT_VIEW', 'ADD_TO_CART', 'CHECKOUT_STARTED', 'PAYMENT_ATTEMPTED', name='funneleventtype', create_type=False), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('product_id', sa.String(length=255), nullable=True),
        sa.Column('cart_value_paise', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_funnel_events_session_id'), 'funnel_events', ['session_id'], unique=False)
    op.create_index(op.f('ix_funnel_events_timestamp'), 'funnel_events', ['timestamp'], unique=False)
    op.create_index('ix_funnel_events_session_type', 'funnel_events', ['session_id', 'event_type'], unique=False)

    # 4. Update PaymentEvents Table
    op.add_column('payment_events', sa.Column('session_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_payment_events_session_id'), 'payment_events', ['session_id'], unique=False)
    op.create_foreign_key(None, 'payment_events', 'sessions', ['session_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Reverse PaymentEvents changes
    op.drop_constraint(None, 'payment_events', type_='foreignkey')
    op.drop_index(op.f('ix_payment_events_session_id'), table_name='payment_events')
    op.drop_column('payment_events', 'session_id')

    # Drop tables
    op.drop_index('ix_funnel_events_session_type', table_name='funnel_events')
    op.drop_index(op.f('ix_funnel_events_timestamp'), table_name='funnel_events')
    op.drop_index(op.f('ix_funnel_events_session_id'), table_name='funnel_events')
    op.drop_table('funnel_events')

    op.drop_index(op.f('ix_sessions_customer_id'), table_name='sessions')
    op.drop_table('sessions')

    # Drop Enum
    op.execute("DROP TYPE funneleventtype")
