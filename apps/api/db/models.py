"""
RecoverFlow API — SQLAlchemy ORM models.

Why this file exists:
  Single source of truth for the database schema.  Alembic migrations are
  auto-generated from these model definitions, so the schema can never drift
  from the code.  All tables match the field lists in PRD Section 20.

Conventions:
  - Every table has `id` (UUID primary key), `created_at`, and (where mutable)
    `updated_at` columns.
  - Timestamps are stored as TIMESTAMPTZ (UTC) in Postgres.
  - String enums are implemented as Python Enum classes mapped to VARCHAR so
    that values are readable in raw SQL queries.
  - Foreign keys use ON DELETE RESTRICT by default to prevent orphaned records.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# Enum types
# ---------------------------------------------------------------------------


class CustomerSegment(str, enum.Enum):
    """Customer value segments used for risk and intervention ranking."""

    HIGH_VALUE = "HIGH_VALUE"
    MEDIUM_VALUE = "MEDIUM_VALUE"
    LOW_VALUE = "LOW_VALUE"
    CHURNED = "CHURNED"


class SubscriptionStatus(str, enum.Enum):
    """Lifecycle states of a merchant subscription."""

    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    HALTED = "HALTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentEventStatus(str, enum.Enum):
    """Processing status of an ingested webhook event."""

    RECEIVED = "RECEIVED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class FailureType(str, enum.Enum):
    """Root-cause classification for a failed payment."""

    TEMPORARY = "TEMPORARY"
    PAYMENT_METHOD = "PAYMENT_METHOD"
    PERSISTENT = "PERSISTENT"
    CUSTOMER_ACTION = "CUSTOMER_ACTION"
    UNKNOWN = "UNKNOWN"


class CaseStatus(str, enum.Enum):
    """State machine states for a recovery case."""

    OPEN = "OPEN"
    ANALYZING = "ANALYZING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    ACTION_INITIATED = "ACTION_INITIATED"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    UNRECOVERABLE = "UNRECOVERABLE"
    SUPPRESSED = "SUPPRESSED"


class ActionType(str, enum.Enum):
    """Whitelisted action types the system can execute."""

    RETRY = "RETRY"
    PAYMENT_LINK = "PAYMENT_LINK"
    INVOICE = "INVOICE"
    PAYMENT_METHOD_UPDATE = "PAYMENT_METHOD_UPDATE"
    REMINDER = "REMINDER"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    NO_ACTION = "NO_ACTION"


class AuthorizationStatus(str, enum.Enum):
    """Policy engine decision for an action."""

    AUTONOMOUS = "AUTONOMOUS"
    AWAITING_HUMAN = "AWAITING_HUMAN"
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


class ExecutionStatus(str, enum.Enum):
    """Execution state of an action after authorization."""

    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"
    EXCEPTION = "EXCEPTION"
    VALIDATION_BLOCKED = "VALIDATION_BLOCKED"


class RiskLevel(str, enum.Enum):
    """Risk classification from the Risk Firewall."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AuditEventType(str, enum.Enum):
    """Types of audit events written to the immutable audit log."""

    CASE_CREATED = "CASE_CREATED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    PREDICTION_COMPLETED = "PREDICTION_COMPLETED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    ACTION_AUTHORIZED = "ACTION_AUTHORIZED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    OUTCOME_VERIFIED = "OUTCOME_VERIFIED"
    CASE_CLOSED = "CASE_CLOSED"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    LLM_EXPLANATION_FAILED = "LLM_EXPLANATION_FAILED"
    # Failure Center track events
    WEBHOOK_DUPLICATE_DROPPED = "WEBHOOK_DUPLICATE_DROPPED"
    VALIDATION_BLOCKED = "VALIDATION_BLOCKED"
    ACTION_TIMEOUT = "ACTION_TIMEOUT"
    RECONCILIATION_EXCEPTION = "RECONCILIATION_EXCEPTION"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    # Risk Firewall events — reason codes always start with "RISK_" prefix
    # so they are distinguishable from Policy Engine events ("POLICY_" prefix)
    RISK_FIREWALL_EVALUATED = "RISK_FIREWALL_EVALUATED"
    RISK_FIREWALL_BLOCKED = "RISK_FIREWALL_BLOCKED"



class ReconciliationStatus(str, enum.Enum):
    """Status of a financial reconciliation record."""

    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    EXCEPTION = "EXCEPTION"
    PENDING = "PENDING"


class FunnelEventType(str, enum.Enum):
    """Stages of the synthetic revenue funnel."""
    
    SITE_VISIT = "SITE_VISIT"
    PRODUCT_VIEW = "PRODUCT_VIEW"
    ADD_TO_CART = "ADD_TO_CART"
    CHECKOUT_STARTED = "CHECKOUT_STARTED"
    PAYMENT_ATTEMPTED = "PAYMENT_ATTEMPTED"


# ---------------------------------------------------------------------------
# Helper: shared timestamp columns
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """Return current UTC datetime (used as server-side default)."""
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------


class Merchant(Base):
    """
    A merchant account in RecoverFlow.

    Why: Every recovery case, policy, and customer is scoped to a merchant.
    This enables future multi-tenancy without schema changes.
    """

    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    razorpay_account_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    customers: Mapped[list[Customer]] = relationship(back_populates="merchant")
    policies: Mapped[list[Policy]] = relationship(back_populates="merchant")


class Customer(Base):
    """
    A customer belonging to a merchant.

    Why: Customer history (segment, tenure, payment behaviour) is a primary
    input to recoverability prediction and intervention ranking.
    """

    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    segment: Mapped[CustomerSegment] = mapped_column(
        Enum(CustomerSegment), nullable=False, default=CustomerSegment.MEDIUM_VALUE
    )
    # Tenure in days since first payment
    tenure_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    merchant: Mapped[Merchant] = relationship(back_populates="customers")
    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="customer"
    )


class Subscription(Base):
    """
    A subscription plan held by a customer.

    Why: Subscription context (amount, cycle, status) is essential for
    understanding failure severity and recovery window.
    """

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Razorpay subscription ID for cross-referencing
    external_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    plan_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Amount in smallest currency unit (paise for INR)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE
    )
    # Billing cycle number (1, 2, 3 …)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    customer: Mapped[Customer] = relationship(back_populates="subscriptions")
    recovery_cases: Mapped[list[RecoveryCase]] = relationship(
        back_populates="subscription"
    )


class PaymentEvent(Base):
    """
    A raw, immutable record of every inbound webhook event.

    Why: Separating raw event storage from business logic enables idempotency
    (duplicate check on external_event_id) and full replay capability.
    The payload_hash is used to detect bitwise-identical duplicate submissions.
    """

    __tablename__ = "payment_events"
    __table_args__ = (
        UniqueConstraint("external_event_id", name="uq_payment_events_external_id"),
        Index("ix_payment_events_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The event ID from the upstream provider (e.g. Razorpay webhook event ID).
    # This is the primary idempotency key — unique constraint enforced above.
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # SHA-256 hex digest of the raw payload — used to detect identical resends.
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Raw JSON payload preserved for replay / auditing.
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[PaymentEventStatus] = mapped_column(
        Enum(PaymentEventStatus),
        nullable=False,
        default=PaymentEventStatus.RECEIVED,
    )
    # Foreign key to the recovery case created (if any) from this event.
    recovery_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Phase 9: Link back to the synthetic top-of-funnel session that originated this payment
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )


class RecoveryCase(Base):
    """
    The central entity representing a failed payment that requires intervention.

    Why: A recovery case aggregates the payment event, customer context,
    ML predictions, risk scores, candidate actions, and final outcome into a
    single state-machine-managed record.  Its status field is the canonical
    source of truth for where a case is in the recovery workflow.
    """

    __tablename__ = "recovery_cases"
    __table_args__ = (Index("ix_recovery_cases_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # The triggering payment event
    payment_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Razorpay payment ID for cross-referencing with provider APIs
    external_payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Amount in paise
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failure_type: Mapped[FailureType] = mapped_column(
        Enum(FailureType), nullable=False, default=FailureType.UNKNOWN
    )
    # ML output: P(recovery within window) — null until analysis runs
    recoverability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Risk Firewall output
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[RiskLevel | None] = mapped_column(
        Enum(RiskLevel), nullable=True
    )
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus), nullable=False, default=CaseStatus.OPEN
    )
    # LLM-generated human-readable explanation (stored for display + audit)
    llm_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Model version tags so predictions are traceable
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    subscription: Mapped[Subscription | None] = relationship(
        back_populates="recovery_cases"
    )
    customer: Mapped[Customer | None] = relationship(
        foreign_keys="[RecoveryCase.customer_id]"
    )
    payment_event: Mapped[PaymentEvent | None] = relationship(
        foreign_keys="[RecoveryCase.payment_event_id]"
    )
    candidate_actions: Mapped[list[CandidateAction]] = relationship(
        back_populates="case"
    )
    actions: Mapped[list[Action]] = relationship(back_populates="case")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="case")
    reconciliation_records: Mapped[list[ReconciliationRecord]] = relationship(
        back_populates="case"
    )


class CandidateAction(Base):
    """
    A ranked intervention option generated by the AI engine for a given case.

    Why: Storing all candidate actions (not just the chosen one) is essential
    for explainability — the dashboard shows why a particular intervention
    was preferred over alternatives.
    """

    __tablename__ = "candidate_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType), nullable=False
    )
    # P(success | case, this action)
    success_probability: Mapped[float] = mapped_column(Float, nullable=False)
    # Expected value = amount x success_probability (in paise)
    expected_value_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # The estimated execution cost of this specific action (in paise)
    action_cost_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel), nullable=False, default=RiskLevel.LOW
    )
    # Ranking position (1 = best)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    case: Mapped[RecoveryCase] = relationship(back_populates="candidate_actions")


class Action(Base):
    """
    An action that was actually authorized and (attempted to be) executed.

    Why: Separating authorized actions from candidates creates a clear audit
    trail.  An action row is only created when the Policy Engine says ALLOW or
    HUMAN_APPROVED — never before.
    """

    __tablename__ = "actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType), nullable=False
    )
    authorization_status: Mapped[AuthorizationStatus] = mapped_column(
        Enum(AuthorizationStatus),
        nullable=False,
        default=AuthorizationStatus.AWAITING_HUMAN,
    )
    execution_status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING
    )
    # Reference ID returned by the payment provider (e.g. Razorpay payment link ID)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Idempotency key used when calling the provider API
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    case: Mapped[RecoveryCase] = relationship(back_populates="actions")
    reconciliation_records: Mapped[list[ReconciliationRecord]] = relationship(
        back_populates="action"
    )


class Policy(Base):
    """
    Merchant-defined recovery policy guardrails.

    Why: The Policy Engine reads these rows — not hardcoded defaults — before
    authorising any autonomous action.  Merchants configure them through the
    Policy Studio UI.  Changes are versioned via updated_at for auditability.
    """

    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Maximum amount (in paise) allowed for autonomous action
    max_autonomous_amount_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=500_000  # ₹5,000
    )
    # Maximum number of automated interventions per case
    retry_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    # Minimum hours between interventions for the same case
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    # Minimum model confidence required for autonomous action (0.0-1.0)
    confidence_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.80
    )
    # Cases above this amount (paise) require human approval
    human_review_threshold_paise: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=2_500_000  # ₹25,000
    )
    # Portfolio-level budget limit for recovery actions (in paise)
    max_recovery_spend_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Max customer-facing contacts per 72-hour window
    max_contacts_per_72h: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    # Policy version label for auditability
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    merchant: Mapped[Merchant] = relationship(back_populates="policies")


class AuditEvent(Base):
    """
    Immutable audit log entry for every significant system decision.

    Why: Every financial action — whether ALLOW, REVIEW, or BLOCK — must
    produce an audit row.  This table is append-only by convention; rows
    should never be updated or deleted.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_case_id", "case_id"),
        Index("ix_audit_events_timestamp", "timestamp"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType), nullable=False
    )
    # Version tags so every log entry is traceable to a model/policy snapshot
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # The decision made (e.g. "AUTONOMOUS", "BLOCKED", "HUMAN_ESCALATION")
    decision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Human-readable reason for the decision
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Additional structured context (feature values, scores, etc.)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    case: Mapped[RecoveryCase | None] = relationship(back_populates="audit_events")


class ReconciliationRecord(Base):
    """
    Finance Truth Layer reconciliation between an executed action and payment outcome.

    Why: An action being "successful" (e.g. payment link sent) must never be
    conflated with money actually being received.  This table separates the
    two and surfaces discrepancies as exceptions for human review.
    """

    __tablename__ = "reconciliation_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # What the action was supposed to recover (in paise)
    expected_amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # What was actually captured according to the payment provider
    actual_amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus),
        nullable=False,
        default=ReconciliationStatus.PENDING,
    )
    # Human-readable description of any mismatch / exception
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    case: Mapped[RecoveryCase] = relationship(back_populates="reconciliation_records")
    action: Mapped[Action] = relationship(back_populates="reconciliation_records")


class Session(Base):
    """
    A top-of-funnel customer session. Used to map the Revenue Leak Graph.
    This data is predominantly syntheticly generated for demo purposes.
    """
    __tablename__ = "sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Anonymous sessions exist prior to login/checkout
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Device, browser, channel metadata
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    
    events: Mapped[list[FunnelEvent]] = relationship(back_populates="session")


class FunnelEvent(Base):
    """
    An event occurring within a Session, mapping to the funnel stages.
    """
    __tablename__ = "funnel_events"
    __table_args__ = (
        Index("ix_funnel_events_session_type", "session_id", "event_type"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_type: Mapped[FunnelEventType] = mapped_column(
        Enum(FunnelEventType), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    product_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cart_value_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    session: Mapped[Session] = relationship(back_populates="events")

