"""
Integration tests for Budget Safety guarantees.

Why this exists:
  Ensures that even if the Budget Optimizer marks a candidate action as "funded"
  (great expected value, fits within budget), the downstream safety gates
  (Policy Engine + Risk Firewall) still evaluate the action and can BLOCK or
  hold it for human review at decision time.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.api.db.models import (
    Action,
    ActionType,
    AuthorizationStatus,
    FailureType,
    Merchant,
    Policy,
    RecoveryCase,
)
from domain.policies.pipeline import run_decision_pipeline
from domain.recovery.budget_optimizer import CandidateOptimizationInput, optimize_budget

import os
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://recoverflow:recoverflow@localhost:5432/recoverflow")

@pytest_asyncio.fixture
async def db_engine_and_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield test_engine, TestingSessionLocal
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_budget_funded_action_can_be_blocked_by_risk_firewall(db_engine_and_session):
    """
    Ensures that even if the Budget Optimizer marks a candidate action as "funded" (because
    it has a great expected value and fits in the budget), the existing safety gates
    (like Phase 6 Risk Firewall) still evaluate the action and can BLOCK it at execution time.
    """
    engine, Session = db_engine_and_session
    async with Session() as db_session:
        merchant = Merchant(name="Budget Safety Test Merchant")
        db_session.add(merchant)
        await db_session.flush()

        # Policy allows only tiny autonomous amounts, so a massive case must NOT be AUTONOMOUS
        policy = Policy(
            merchant_id=merchant.id,
            max_autonomous_amount_paise=5000,
            human_review_threshold_paise=10000,
        )
        db_session.add(policy)

        case = RecoveryCase(
            merchant_id=merchant.id,
            amount_paise=999_999_999_9,  # Massive amount, will trigger amount risk gates
            failure_type=FailureType.TEMPORARY,
        )
        db_session.add(case)
        await db_session.commit()

        # 1. Optimizer runs (Simulation): huge budget, free cost, huge ROI -> Definitely funded
        candidates = [
            CandidateOptimizationInput(
                case_id=str(case.id),
                action_type=ActionType.PAYMENT_LINK.value,
                expected_recovery_paise=500000,
                action_cost_paise=0
            )
        ]
        allocations = optimize_budget(candidates, budget_paise=1000000)
        assert allocations[0].funded is True

        # 2. Run the real decision pipeline (Policy Engine + Risk Firewall)
        await run_decision_pipeline(db_session, case)
        await db_session.commit()

        # 3. It should NOT be AUTONOMOUS despite being funded by the optimizer
        from sqlalchemy import select
        actions_res = await db_session.execute(select(Action).where(Action.case_id == case.id))
        actions = actions_res.scalars().all()
        assert len(actions) == 1
        assert actions[0].authorization_status in (
            AuthorizationStatus.BLOCKED,
            AuthorizationStatus.AWAITING_HUMAN,
        )
