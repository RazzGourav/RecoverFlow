"""
Simulation Core Engine for RecoverFlow (Phase 11)

Provides a dry-run execution environment for candidate strategies across batches of cases.
Guarantees zero database mutations by wrapping all execution in a nested transaction
and forcing a rollback.
"""
import uuid
import structlog
from typing import List
from unittest.mock import patch
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RecoveryCase, Action, ActionType, ExecutionStatus, AuthorizationStatus
from domain.policies.pipeline import run_decision_pipeline
from domain.finance.executor import execute_action
from domain.recovery.budget_optimizer import optimize_budget, CandidateOptimizationInput

logger = structlog.get_logger(__name__)

# Static cost assumptions for simulation in paise (1 INR = 100 paise)
ACTION_COSTS = {
    "NO_ACTION": 0,
    "REMINDER_ONLY": 0,       # Email/SMS usually trivial cost, assume 0 for optimizer scale
    "PAYMENT_LINK": 0,
    "DISCOUNT_5": 5,          # Placeholder relative cost, but actual cost is 5% of amount
    "DISCOUNT_10": 10,        # 10% of amount
    "RETRY_PLUS_REMINDER": 0
}

def get_action_cost(action_type: str, amount_paise: int) -> int:
    """Calculates the cost of an action in paise."""
    if action_type == "DISCOUNT_5":
        return int(amount_paise * 0.05)
    elif action_type == "DISCOUNT_10":
        return int(amount_paise * 0.10)
    return ACTION_COSTS.get(action_type, 0)

class SimulationResult(BaseModel):
    strategy: str
    expected_recovery_paise: int
    cost_paise: int
    net_recovery_paise: int
    cases_processed: int

async def _mock_validation(*args, **kwargs):
    from integrations.validation import ValidationOutcome, ValidationStatus
    return ValidationOutcome(status=ValidationStatus.VALID, reason="Simulation Override")

async def simulate_strategy_batch(
    session: AsyncSession,
    case_ids: List[uuid.UUID],
    strategy: str,
    budget_paise: int
) -> SimulationResult:
    """
    Runs a batch of cases through the decision pipeline in dry-run mode.
    
    Args:
        session: Active SQLAlchemy session.
        case_ids: List of RecoveryCase UUIDs to simulate.
        strategy: "RECOVERFLOW_OPTIMAL" or a forced ActionType (e.g. "REMINDER_ONLY").
        budget_paise: The simulated budget available for the optimizer.
        
    Returns:
        SimulationResult containing metrics.
    """
    total_expected_recovery = 0
    total_cost = 0
    cases_processed = 0

    # Ensure zero side-effects via a nested transaction that rolls back at the end.
    original_commit = session.commit
    original_rollback = session.rollback
    
    async def mock_commit():
        await session.flush()
        
    async def mock_rollback():
        pass
        
    session.commit = mock_commit
    session.rollback = mock_rollback

    async with session.begin_nested() as nested:
        try:
            # 1. Fetch cases
            stmt = select(RecoveryCase).where(RecoveryCase.id.in_(case_ids))
            result = await session.execute(stmt)
            cases = result.scalars().all()
            
            # Map for RECOVERFLOW_OPTIMAL optimizer funding logic
            funded_cases = set(case_ids)  # Default all funded for forced strategies
            
            # Phase 8.5 Optimizer integration for the OPTIMAL strategy
            if strategy == "RECOVERFLOW_OPTIMAL":
                import pandas as pd
                from ai.features.engineer import build_features, ACTION_TYPES
                from ai.inference import predict
                from domain.policies.pipeline import build_case_context
                
                predict.load_models()
                candidates = []
                for case in cases:
                    context = build_case_context(case)
                    df = pd.DataFrame([context])
                    X_base = build_features(df)
                    
                    best_ev = -1
                    best_action = "NO_ACTION"
                    best_prob = 0.0
                    
                    for a in ACTION_TYPES:
                        X_action = X_base.copy()
                        for act in ACTION_TYPES:
                            X_action[f"action_{act}"] = 1 if act == a else 0
                        prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
                        ev = int(case.amount_paise * prob)
                        if ev > best_ev:
                            best_ev = ev
                            best_action = a
                            best_prob = prob
                            
                    cost = get_action_cost(best_action, case.amount_paise)
                    candidates.append(
                        CandidateOptimizationInput(
                            case_id=str(case.id),
                            action_type=best_action,
                            expected_recovery_paise=best_ev,
                            action_cost_paise=cost
                        )
                    )
                
                allocations = optimize_budget(candidates, budget_paise)
                funded_cases = {uuid.UUID(a.case_id) for a in allocations if a.funded}

            # 2. Prevent ARQ job enqueueing and Mock External Calls
            with patch("integrations.factory.get_validator") as mock_get_val, \
                 patch("integrations.factory.get_provider") as mock_get_prov:
                 
                # Mock the validator to always pass
                mock_validator = mock_get_val.return_value
                mock_validator.return_value.status.value = "VALID"
                mock_validator.return_value.reason = "Simulation Passed"
                
                # We need the validator outcome to be exactly ValidationOutcome with status VALID
                from integrations.validation import ValidationOutcome, ValidationStatus
                mock_validator.return_value = ValidationOutcome(status=ValidationStatus.VALID, reason="Simulation")

                # Mock provider to not actually hit Razorpay
                mock_provider = mock_get_prov.return_value
                async def fake_create_link(*args, **kwargs):
                    return "simulated_link_" + str(uuid.uuid4())
                mock_provider.create_payment_link = fake_create_link
                async def fake_fetch_payment(*args, **kwargs):
                    return {}
                mock_provider.fetch_payment = fake_fetch_payment

                for case in cases:
                    # Determine force_action
                    force_action = None
                    if strategy != "RECOVERFLOW_OPTIMAL":
                        try:
                            force_action = ActionType(strategy)
                        except ValueError:
                            force_action = ActionType.NO_ACTION
                    else:
                        if case.id not in funded_cases:
                            force_action = ActionType.NO_ACTION

                    # Run decision pipeline (Phase 3 inference + Phase 6 risk + Phase 4 policy)
                    await run_decision_pipeline(session, case, force_action=force_action)
                    
                    # The pipeline generates an Action row in the session.
                    # We fetch it to execute it.
                    action_stmt = select(Action).where(Action.case_id == case.id).order_by(Action.created_at.desc()).limit(1)
                    action_res = await session.execute(action_stmt)
                    action = action_res.scalar_one_or_none()
                    
                    if action and action.execution_status == ExecutionStatus.PENDING:
                        # Force approval in simulation so it can be executed
                        action.authorization_status = AuthorizationStatus.APPROVED
                        # Fake Execution (Phase 7 Execution) without calling real executor to avoid NotImplementedError
                        action.execution_status = ExecutionStatus.EXECUTED
                        action.provider_reference = f"simulated_exec_{uuid.uuid4()}"
                        session.add(action)
                        
                    # Calculate Expected Value resulting from the ACTUAL action that made it through
                    if action and action.execution_status == ExecutionStatus.EXECUTED and action.action_type != ActionType.NO_ACTION:
                        # Fetch the candidate action to get the expected probability
                        from db.models import CandidateAction
                        cand_stmt = select(CandidateAction).where(
                            CandidateAction.case_id == case.id, 
                            CandidateAction.action_type == action.action_type
                        ).limit(1)
                        cand_res = await session.execute(cand_stmt)
                        candidate = cand_res.scalar_one_or_none()
                        
                        prob = candidate.success_probability if candidate else 0.15 # fallback
                        ev = int(case.amount_paise * prob)
                        cost = get_action_cost(action.action_type.value, case.amount_paise)
                        
                        total_expected_recovery += ev
                        total_cost += cost

                    cases_processed += 1
                    
        finally:
            # Restore original methods
            session.commit = original_commit
            session.rollback = original_rollback
            
            # ZERO writes guarantee: Rollback everything before exiting.
            await nested.rollback()
            
    return SimulationResult(
        strategy=strategy,
        expected_recovery_paise=total_expected_recovery,
        cost_paise=total_cost,
        net_recovery_paise=total_expected_recovery - total_cost,
        cases_processed=cases_processed
    )
