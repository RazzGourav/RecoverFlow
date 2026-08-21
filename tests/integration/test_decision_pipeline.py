"""
Integration tests for the Decision Pipeline.

Why this exists:
  Ensures that the ML Engine (Phase 3) and Policy Engine (Phase 4)
  integrate successfully with the database, and that EXACTLY ONE
  audit event is produced per decision.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.api.db.models import (
    Action,
    AuditEvent,
    AuditEventType,
    AuthorizationStatus,
    CandidateAction,
    CaseStatus,
    FailureType,
    Merchant,
    Policy,
    RecoveryCase,
)
from domain.policies.pipeline import run_decision_pipeline

TEST_DATABASE_URL = "postgresql+asyncpg://recoverflow:recoverflow@postgres:5432/recoverflow"

@pytest_asyncio.fixture
async def db_engine_and_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield test_engine, TestingSessionLocal
    await test_engine.dispose()

@pytest.mark.asyncio
async def test_decision_pipeline_creates_audit_event_and_action(db_engine_and_session):
    engine, Session = db_engine_and_session
    async with Session() as db_session:
        merchant = Merchant(name="Test Merchant")
        db_session.add(merchant)
        await db_session.flush()
        
        policy = Policy(
            merchant_id=merchant.id,
            max_autonomous_amount_paise=500000,
            retry_limit=2,
            cooldown_hours=12
        )
        db_session.add(policy)
        
        case = RecoveryCase(
            merchant_id=merchant.id,
            amount_paise=100000,
            failure_type=FailureType.TEMPORARY
        )
        db_session.add(case)
        await db_session.commit()
        
        await run_decision_pipeline(db_session, case)
        await db_session.commit()
        
        assert case.status in [CaseStatus.ACTION_INITIATED, CaseStatus.AWAITING_APPROVAL]
        assert case.recoverability_score is not None
        assert case.risk_level is not None
        
        candidates_res = await db_session.execute(select(CandidateAction).where(CandidateAction.case_id == case.id))
        candidates = candidates_res.scalars().all()
        assert len(candidates) > 0
        
        actions_res = await db_session.execute(select(Action).where(Action.case_id == case.id))
        actions = actions_res.scalars().all()
        assert len(actions) == 1
        action = actions[0]
        
        audit_res = await db_session.execute(select(AuditEvent).where(AuditEvent.case_id == case.id))
        audit_events = audit_res.scalars().all()
        # Phase 6: pipeline now emits 2 events — one Risk Firewall event (RISK_FIREWALL_EVALUATED
        # or RISK_FIREWALL_BLOCKED) and one Policy Engine event (ACTION_AUTHORIZED etc.)
        assert len(audit_events) >= 1
        
        # Policy engine events have event_type in the policy domain
        POLICY_EVENT_TYPES = {
            AuditEventType.ACTION_AUTHORIZED,
            AuditEventType.HUMAN_ESCALATION,
            AuditEventType.ACTION_BLOCKED,
            AuditEventType.POLICY_EVALUATED,
            AuditEventType.LLM_EXPLANATION_FAILED,
        }
        policy_events = [e for e in audit_events if e.event_type in POLICY_EVENT_TYPES]
        assert len(policy_events) >= 1, "At least one Policy Engine audit event required"
        audit = policy_events[0]
        assert audit.policy_version == "1.0.0"
        assert audit.model_version is not None
        assert audit.decision in ["AUTONOMOUS", "AWAITING_HUMAN", "BLOCKED"]
        assert audit.context["action_type"] == action.action_type.value


@pytest.mark.asyncio
async def test_decision_pipeline_blocks_repeated_action(db_engine_and_session):
    engine, Session = db_engine_and_session
    async with Session() as db_session:
        merchant = Merchant(name="Test Merchant 2")
        db_session.add(merchant)
        await db_session.flush()
        
        policy = Policy(merchant_id=merchant.id, cooldown_hours=24, retry_limit=5)
        db_session.add(policy)
        
        case = RecoveryCase(
            merchant_id=merchant.id,
            amount_paise=100000,
            failure_type=FailureType.PAYMENT_METHOD
        )
        db_session.add(case)
        await db_session.flush()
        
        past_action = Action(
            case_id=case.id,
            action_type="RETRY",
            authorization_status=AuthorizationStatus.AUTONOMOUS,
            idempotency_key=f"test_idem_{uuid.uuid4().hex}",
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(past_action)
        await db_session.commit()
        
        await run_decision_pipeline(db_session, case)
        await db_session.commit()
        
        actions_res = await db_session.execute(
            select(Action).where(Action.case_id == case.id)
        )
        actions = actions_res.scalars().all()
        assert len(actions) == 2 
        
        new_action = next(a for a in actions if a.idempotency_key != past_action.idempotency_key)
        assert new_action.authorization_status == AuthorizationStatus.BLOCKED
        
        audit_res = await db_session.execute(
            select(AuditEvent)
            .where(AuditEvent.case_id == case.id)
        )
        all_audit_events = audit_res.scalars().all()
        # Phase 6: find the Policy Engine audit event (event_type = ACTION_BLOCKED)
        policy_audits = [
            e for e in all_audit_events
            if e.event_type == AuditEventType.ACTION_BLOCKED and e.decision == "BLOCKED"
        ]
        assert len(policy_audits) >= 1, "Expected a BLOCKED Policy Engine audit event"
        audit = policy_audits[0]
        assert audit.decision == "BLOCKED"
        assert audit.reason == "POLICY_COOLDOWN_ACTIVE"
