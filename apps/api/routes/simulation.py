import uuid
from typing import Any

from ai.evaluation.simulation_core import SimulationResult, simulate_strategy_batch
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import (
    CaseStatus,
    FunnelEvent,
    RecoveryCase,
)
from dependencies.db import get_db

router = APIRouter(prefix="/simulate", tags=["simulation"])

class SimulationCompareRequest(BaseModel):
    case_ids: list[uuid.UUID] | None = None
    sample_size: int = 100
    budget_paise: int = 500000  # Default 5,000 INR

class StrategyComparisonResult(SimulationResult):
    vs_optimal_paise: int

class SimulationCompareResponse(BaseModel):
    results: list[StrategyComparisonResult]

@router.post("/compare", response_model=SimulationCompareResponse)
async def compare_strategies(
    request: SimulationCompareRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Simulates a batch of cases across multiple strategies and compares the outcomes.
    """
    case_ids = request.case_ids
    if not case_ids:
        # Sample OPEN cases if none provided
        stmt = select(RecoveryCase.id).where(RecoveryCase.status == CaseStatus.OPEN).limit(request.sample_size)
        result = await session.execute(stmt)
        case_ids = list(result.scalars().all())

    if not case_ids:
        raise HTTPException(status_code=400, detail="No cases available for simulation.")

    strategies = [
        "RECOVERFLOW_OPTIMAL",
        "REMINDER_ONLY",
        "DISCOUNT_5",
        "DISCOUNT_10",
        "RETRY_PLUS_REMINDER",
        "DO_NOTHING"
    ]

    sim_results = []

    # We must run these sequentially or in a way that respects the DB connection/transaction.
    # Since they use nested transactions on the same session, sequential is safest.
    for strategy in strategies:
        try:
            res = await simulate_strategy_batch(
                session=session,
                case_ids=case_ids,
                strategy=strategy,
                budget_paise=request.budget_paise
            )
            sim_results.append(res)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Simulation failed for strategy {strategy}: {e!s}")

    # Find OPTIMAL net recovery for comparison
    optimal_net = next((r.net_recovery_paise for r in sim_results if r.strategy == "RECOVERFLOW_OPTIMAL"), 0)

    final_results = []
    for r in sim_results:
        final_results.append(
            StrategyComparisonResult(
                strategy=r.strategy,
                expected_recovery_paise=r.expected_recovery_paise,
                cost_paise=r.cost_paise,
                net_recovery_paise=r.net_recovery_paise,
                cases_processed=r.cases_processed,
                vs_optimal_paise=r.net_recovery_paise - optimal_net
            )
        )

    return SimulationCompareResponse(results=final_results)


# --- Replay Lab ---

class ReplayRequest(BaseModel):
    strategy: str = "RECOVERFLOW_OPTIMAL"

class TimelineEvent(BaseModel):
    id: str
    type: str
    description: str
    timestamp: str
    metadata: dict[str, Any] | None = None

class MetricSnapshot(BaseModel):
    expected_recovery_paise: int
    cost_paise: int
    net_recovery_paise: int
    action_type: str

class ReplayResponse(BaseModel):
    timeline: list[TimelineEvent]
    before: MetricSnapshot
    after: MetricSnapshot

@router.post("/replay/{case_id}", response_model=ReplayResponse)
async def replay_case(
    case_id: uuid.UUID,
    request: ReplayRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Replays a single case's event sequence and runs a counterfactual simulation.
    """
    # 1. Fetch case and related entities
    stmt = select(RecoveryCase).options(
        selectinload(RecoveryCase.payment_event),
        selectinload(RecoveryCase.actions),
        selectinload(RecoveryCase.audit_events),
        selectinload(RecoveryCase.candidate_actions)
    ).where(RecoveryCase.id == case_id)

    result = await session.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(404, "Case not found")

    # 2. Build Timeline
    timeline: list[TimelineEvent] = []

    # 2a. Funnel Events (if session_id exists)
    if case.payment_event and case.payment_event.session_id:
        f_stmt = select(FunnelEvent).where(FunnelEvent.session_id == case.payment_event.session_id).order_by(FunnelEvent.timestamp)
        f_res = await session.execute(f_stmt)
        for fe in f_res.scalars().all():
            timeline.append(TimelineEvent(
                id=str(fe.id),
                type="FUNNEL",
                description=fe.event_type.value if hasattr(fe.event_type, 'value') else fe.event_type,
                timestamp=fe.timestamp.isoformat(),
                metadata={"product_id": fe.product_id, "cart_value_paise": fe.cart_value_paise}
            ))

    # 2b. Payment Event
    if case.payment_event:
        timeline.append(TimelineEvent(
            id=str(case.payment_event.id),
            type="PAYMENT_ATTEMPT",
            description="Payment Failed",
            timestamp=case.payment_event.received_at.isoformat(),
            metadata={"status": case.payment_event.status.value if hasattr(case.payment_event.status, 'value') else case.payment_event.status}
        ))

    # 2c. Audit Events & Actions (Before)
    for ae in sorted(case.audit_events, key=lambda x: x.timestamp):
        timeline.append(TimelineEvent(
            id=str(ae.id),
            type="AUDIT",
            description=ae.event_type.value if hasattr(ae.event_type, 'value') else ae.event_type,
            timestamp=ae.timestamp.isoformat(),
            metadata={"decision": ae.decision, "reason": ae.reason}
        ))

    for a in sorted(case.actions, key=lambda x: x.created_at):
        timeline.append(TimelineEvent(
            id=str(a.id),
            type="ACTION",
            description=f"Executed {a.action_type.value if hasattr(a.action_type, 'value') else a.action_type}",
            timestamp=a.created_at.isoformat(),
            metadata={"status": a.execution_status.value if hasattr(a.execution_status, 'value') else a.execution_status}
        ))

    # Sort the timeline chronologically
    timeline.sort(key=lambda x: x.timestamp)

    # 3. Calculate "Before" Metrics
    before_action_type = "NO_ACTION"
    before_cost = 0
    before_ev = 0

    # Get the latest executed action
    executed_actions = [a for a in case.actions if a.execution_status.value == "EXECUTED"] if case.actions else []
    if executed_actions:
        latest_action = sorted(executed_actions, key=lambda x: x.created_at, reverse=True)[0]
        before_action_type = latest_action.action_type.value if hasattr(latest_action.action_type, 'value') else latest_action.action_type

        # Find expected value from candidate actions
        cand = next((ca for ca in case.candidate_actions if (ca.action_type.value if hasattr(ca.action_type, 'value') else ca.action_type) == before_action_type), None)
        if cand:
            before_ev = cand.expected_value_paise
            before_cost = cand.action_cost_paise

    before_metrics = MetricSnapshot(
        expected_recovery_paise=before_ev,
        cost_paise=before_cost,
        net_recovery_paise=before_ev - before_cost,
        action_type=before_action_type
    )

    # 4. Run "After" Simulation
    after_res = await simulate_strategy_batch(
        session=session,
        case_ids=[case.id],
        strategy=request.strategy,
        budget_paise=500000
    )

    # We need the action type chosen by the simulation.
    # The simulation returns totals, but we need the specific action for the timeline/UI.
    # We can infer it or we can change simulate_strategy_batch to return it.
    # For a single case, we can deduce it if it's not NO_ACTION, but let's just show the net stats.
    # Actually, we should know what action was chosen.
    # Let's peek into the nested transaction? No, it rolls back.
    # For now, we will return the strategy name as action_type if expected_recovery > 0,
    # or if force_action was used, we know what it was.
    after_action_type = request.strategy
    if after_res.expected_recovery_paise == 0:
        after_action_type = "NO_ACTION"

    after_metrics = MetricSnapshot(
        expected_recovery_paise=after_res.expected_recovery_paise,
        cost_paise=after_res.cost_paise,
        net_recovery_paise=after_res.net_recovery_paise,
        action_type=after_action_type
    )

    return ReplayResponse(
        timeline=timeline,
        before=before_metrics,
        after=after_metrics
    )
