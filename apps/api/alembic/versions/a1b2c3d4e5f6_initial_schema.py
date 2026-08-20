"""
Initial database schema — all 10 tables from PRD Section 20.

Revision ID: a1b2c3d4e5f6
Revises: (none — this is the first migration)
Create Date: 2026-08-20

Why this migration exists:
  Bootstrap the complete schema for Phase 0 so that `alembic upgrade head`
  on a fresh Postgres instance produces a fully operational database.

  All tables match the field specifications in PRD Section 20.
  Foreign keys, indexes on external_event_id (idempotency), and
  created_at/updated_at timestamps are included on every table.

  Enum types are created explicitly as Postgres TYPE objects so they appear
  in the database catalog and can be referenced by name.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Enum helpers — we define them once and reuse them in table definitions.
# ---------------------------------------------------------------------------

customer_segment_enum = postgresql.ENUM(
    "HIGH_VALUE", "MEDIUM_VALUE", "LOW_VALUE", "CHURNED",
    name="customersegment", create_type=True
)
subscription_status_enum = postgresql.ENUM(
    "ACTIVE", "PENDING", "HALTED", "CANCELLED", "EXPIRED",
    name="subscriptionstatus", create_type=True
)
payment_event_status_enum = postgresql.ENUM(
    "RECEIVED", "PROCESSING", "PROCESSED", "DUPLICATE", "FAILED",
    name="paymenteventstatus", create_type=True
)
failure_type_enum = postgresql.ENUM(
    "TEMPORARY", "PAYMENT_METHOD", "PERSISTENT", "CUSTOMER_ACTION", "UNKNOWN",
    name="failuretype", create_type=True
)
case_status_enum = postgresql.ENUM(
    "OPEN", "ANALYZING", "AWAITING_APPROVAL", "ACTION_INITIATED",
    "VERIFYING", "RECOVERED", "UNRECOVERABLE", "SUPPRESSED",
    name="casestatus", create_type=True
)
action_type_enum = postgresql.ENUM(
    "RETRY", "PAYMENT_LINK", "INVOICE", "PAYMENT_METHOD_UPDATE",
    "REMINDER", "HUMAN_ESCALATION", "NO_ACTION",
    name="actiontype", create_type=True
)
authorization_status_enum = postgresql.ENUM(
    "AUTONOMOUS", "AWAITING_HUMAN", "APPROVED", "BLOCKED",
    name="authorizationstatus", create_type=True
)
execution_status_enum = postgresql.ENUM(
    "PENDING", "EXECUTING", "SUCCESS", "FAILED", "CANCELLED",
    name="executionstatus", create_type=True
)
risk_level_enum = postgresql.ENUM(
    "LOW", "MEDIUM", "HIGH",
    name="risklevel", create_type=True
)
audit_event_type_enum = postgresql.ENUM(
    "CASE_CREATED", "ANALYSIS_STARTED", "PREDICTION_COMPLETED",
    "POLICY_EVALUATED", "ACTION_AUTHORIZED", "ACTION_BLOCKED",
    "ACTION_EXECUTED", "OUTCOME_VERIFIED", "CASE_CLOSED",
    "HUMAN_ESCALATION", "HUMAN_APPROVED",
    name="auditeventtype", create_type=True
)
reconciliation_status_enum = postgresql.ENUM(
    "MATCHED", "EXCEPTION", "PENDING",
    name="reconciliationstatus", create_type=True
)


def upgrade() -> None:
    """Create all tables in dependency order (FK parents before children)."""

    # --- 1. merchants -------------------------------------------------------
    op.create_table(
        "merchants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("razorpay_account_reference", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_merchants_razorpay_account_reference",
        "merchants",
        ["razorpay_account_reference"],
    )

    # --- 2. customers -------------------------------------------------------
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "merchant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("merchants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_customer_id", sa.String(255), nullable=True),
        sa.Column(
            "segment",
            customer_segment_enum,
            nullable=False,
            server_default="MEDIUM_VALUE",
        ),
        sa.Column("tenure_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_customers_merchant_id", "customers", ["merchant_id"])
    op.create_index(
        "ix_customers_external_customer_id", "customers", ["external_customer_id"]
    )

    # --- 3. subscriptions ---------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_subscription_id", sa.String(255), nullable=True),
        sa.Column("plan_id", sa.String(255), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column(
            "status",
            subscription_status_enum,
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("cycle", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_subscriptions_customer_id", "subscriptions", ["customer_id"]
    )
    op.create_index(
        "ix_subscriptions_external_subscription_id",
        "subscriptions",
        ["external_subscription_id"],
    )

    # --- 4. recovery_cases (created before payment_events for FK) -----------
    op.create_table(
        "recovery_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # payment_event_id FK added below after payment_events is created
        sa.Column("payment_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_payment_id", sa.String(255), nullable=True),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "merchant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("merchants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column(
            "failure_type", failure_type_enum, nullable=False, server_default="UNKNOWN"
        ),
        sa.Column("recoverability_score", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("risk_level", risk_level_enum, nullable=True),
        sa.Column(
            "status", case_status_enum, nullable=False, server_default="OPEN"
        ),
        sa.Column("llm_explanation", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_recovery_cases_status", "recovery_cases", ["status"])
    op.create_index("ix_recovery_cases_merchant_id", "recovery_cases", ["merchant_id"])
    op.create_index(
        "ix_recovery_cases_external_payment_id",
        "recovery_cases",
        ["external_payment_id"],
    )

    # --- 5. payment_events --------------------------------------------------
    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            payment_event_status_enum,
            nullable=False,
            server_default="RECEIVED",
        ),
        sa.Column(
            "recovery_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recovery_cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Idempotency index — UNIQUE constraint on external_event_id prevents
    # duplicate webhook processing at the database level.
    op.create_index(
        "uq_payment_events_external_id",
        "payment_events",
        ["external_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_payment_events_event_type", "payment_events", ["event_type"]
    )
    op.create_index("ix_payment_events_status", "payment_events", ["status"])

    # Now add the deferred FK from recovery_cases → payment_events
    op.create_foreign_key(
        "fk_recovery_cases_payment_event_id",
        "recovery_cases",
        "payment_events",
        ["payment_event_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- 6. candidate_actions -----------------------------------------------
    op.create_table(
        "candidate_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recovery_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", action_type_enum, nullable=False),
        sa.Column("success_probability", sa.Float(), nullable=False),
        sa.Column("expected_value_paise", sa.BigInteger(), nullable=False),
        sa.Column(
            "risk_level", risk_level_enum, nullable=False, server_default="LOW"
        ),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_candidate_actions_case_id", "candidate_actions", ["case_id"]
    )

    # --- 7. actions ---------------------------------------------------------
    op.create_table(
        "actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recovery_cases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action_type", action_type_enum, nullable=False),
        sa.Column(
            "authorization_status",
            authorization_status_enum,
            nullable=False,
            server_default="AWAITING_HUMAN",
        ),
        sa.Column(
            "execution_status",
            execution_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_actions_case_id", "actions", ["case_id"])

    # --- 8. policies --------------------------------------------------------
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "merchant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("merchants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "max_autonomous_amount_paise",
            sa.BigInteger(),
            nullable=False,
            server_default="500000",
        ),
        sa.Column("retry_limit", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False, server_default="12"),
        sa.Column(
            "confidence_threshold", sa.Float(), nullable=False, server_default="0.80"
        ),
        sa.Column(
            "human_review_threshold_paise",
            sa.BigInteger(),
            nullable=False,
            server_default="2500000",
        ),
        sa.Column(
            "max_contacts_per_72h", sa.Integer(), nullable=False, server_default="2"
        ),
        sa.Column("version", sa.String(50), nullable=False, server_default="'1.0.0'"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_policies_merchant_id", "policies", ["merchant_id"])

    # --- 9. audit_events ----------------------------------------------------
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recovery_cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", audit_event_type_enum, nullable=False),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("policy_version", sa.String(50), nullable=True),
        sa.Column("decision", sa.String(100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_audit_events_case_id", "audit_events", ["case_id"])
    op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])

    # --- 10. reconciliation_records -----------------------------------------
    op.create_table(
        "reconciliation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recovery_cases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "action_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("actions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("expected_amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("actual_amount_paise", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            reconciliation_status_enum,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("exception_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_reconciliation_records_case_id", "reconciliation_records", ["case_id"]
    )
    op.create_index(
        "ix_reconciliation_records_action_id", "reconciliation_records", ["action_id"]
    )


def downgrade() -> None:
    """Drop all tables and enum types in reverse dependency order."""
    op.drop_table("reconciliation_records")
    op.drop_table("audit_events")
    op.drop_table("policies")
    op.drop_table("actions")
    op.drop_table("candidate_actions")

    # Drop deferred FK before dropping payment_events
    op.drop_constraint(
        "fk_recovery_cases_payment_event_id", "recovery_cases", type_="foreignkey"
    )
    op.drop_table("payment_events")
    op.drop_table("recovery_cases")
    op.drop_table("subscriptions")
    op.drop_table("customers")
    op.drop_table("merchants")

    # Drop Postgres enum types
    for enum_name in [
        "reconciliationstatus",
        "auditeventtype",
        "risklevel",
        "executionstatus",
        "authorizationstatus",
        "actiontype",
        "casestatus",
        "failuretype",
        "paymenteventstatus",
        "subscriptionstatus",
        "customersegment",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
