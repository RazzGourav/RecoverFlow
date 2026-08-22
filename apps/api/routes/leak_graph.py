"""
RecoverFlow API — Revenue Leak Graph (Phase 9.5)

Produces the full funnel view from top-of-funnel (synthetic) through
payment stage (live system data), with root-cause drill-through at each
leak point.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.db import get_db

try:
    from db.models import (
        ActionType,
        CandidateAction,
        CaseStatus,
        Customer,
        FunnelEvent,
        FunnelEventType,
        PaymentEvent,
        ReconciliationRecord,
        ReconciliationStatus,
        RecoveryCase,
    )
except ImportError:
    from apps.api.db.models import (
        CandidateAction,
        Customer,
        FunnelEvent,
        FunnelEventType,
        PaymentEvent,
        RecoveryCase,
    )

router = APIRouter()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class RootCauseBreakdown(BaseModel):
    failure_type: str
    count: int
    revenue_at_risk_paise: int


class SegmentBreakdown(BaseModel):
    segment: str
    count: int


class RecoveryActionSummary(BaseModel):
    action_type: str
    count: int
    total_expected_recovery_paise: int


class LeakPoint(BaseModel):
    """A transition where users/revenue is lost."""
    from_stage: str
    to_stage: str
    lost_count: int
    lost_value_paise: int
    root_causes: list[RootCauseBreakdown]
    affected_segments: list[SegmentBreakdown]
    recovery_actions: list[RecoveryActionSummary]


class FunnelStage(BaseModel):
    stage: str
    count: int
    value_paise: int
    data_source: str  # "simulated" or "live"


class LeakGraphResponse(BaseModel):
    stages: list[FunnelStage]
    leaks: list[LeakPoint]
    generated_at: str
    note: str = (
        "Top-of-funnel stages (SITE_VISIT through CHECKOUT_STARTED) use "
        "simulated traffic data. Payment-stage-onward data is live system output."
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=LeakGraphResponse)
async def get_leak_graph(db: AsyncSession = Depends(get_db)):
    """
    Full Revenue Leak Graph: funnel stages with counts, values, and
    drill-through at each leak point showing root causes, affected
    segments, and linked recovery actions.
    """

    # 1. Funnel stage counts (from Phase 9 funnel_events)
    funnel_stmt = select(
        FunnelEvent.event_type,
        func.count(FunnelEvent.id),
        func.coalesce(func.sum(FunnelEvent.cart_value_paise), 0)
    ).group_by(FunnelEvent.event_type)
    funnel_result = await db.execute(funnel_stmt)
    funnel_rows = funnel_result.all()

    funnel_stats = {
        row[0]: {"count": row[1], "value": row[2]}
        for row in funnel_rows
    }

    # 2. Payment success counts (from payment_events — live data)
    success_stmt = select(
        func.count(PaymentEvent.id),
        func.coalesce(func.sum(
            func.cast(PaymentEvent.raw_payload['payload']['payment']['entity']['amount'].astext, Integer)
        ), 0)
    ).where(PaymentEvent.event_type == "payment.captured")
    success_result = await db.execute(success_stmt)
    success_row = success_result.one()
    success_count = success_row[0]
    success_value = success_row[1]

    # Build stage list
    simulated_stages = [
        FunnelEventType.SITE_VISIT,
        FunnelEventType.PRODUCT_VIEW,
        FunnelEventType.ADD_TO_CART,
        FunnelEventType.CHECKOUT_STARTED,
    ]

    stages: list[FunnelStage] = []
    for s in simulated_stages:
        stats = funnel_stats.get(s, {"count": 0, "value": 0})
        stages.append(FunnelStage(
            stage=s.value,
            count=stats["count"],
            value_paise=stats["value"],
            data_source="simulated"
        ))

    # PAYMENT_ATTEMPTED from funnel_events (these link to real payment_events)
    pa_stats = funnel_stats.get(FunnelEventType.PAYMENT_ATTEMPTED, {"count": 0, "value": 0})
    stages.append(FunnelStage(
        stage="PAYMENT_ATTEMPTED",
        count=pa_stats["count"],
        value_paise=pa_stats["value"],
        data_source="live"
    ))

    # PAYMENT_SUCCESSFUL — from actual payment_events
    stages.append(FunnelStage(
        stage="PAYMENT_SUCCESSFUL",
        count=success_count,
        value_paise=success_value,
        data_source="live"
    ))

    # 3. Build leak points
    leaks: list[LeakPoint] = []

    # Consecutive stage pairs
    stage_pairs = list(zip(stages[:-1], stages[1:], strict=False))
    for from_stage, to_stage in stage_pairs:
        lost_count = max(0, from_stage.count - to_stage.count)
        lost_value = max(0, from_stage.value_paise - to_stage.value_paise)

        if lost_count == 0:
            leaks.append(LeakPoint(
                from_stage=from_stage.stage,
                to_stage=to_stage.stage,
                lost_count=0,
                lost_value_paise=0,
                root_causes=[],
                affected_segments=[],
                recovery_actions=[]
            ))
            continue

        root_causes: list[RootCauseBreakdown] = []
        affected_segments: list[SegmentBreakdown] = []
        recovery_actions: list[RecoveryActionSummary] = []

        # Only payment-stage leaks have recovery_cases data for drill-through
        if from_stage.stage in ("PAYMENT_ATTEMPTED", "CHECKOUT_STARTED"):
            # Root cause breakdown from recovery_cases via genuine multi-table join
            rc_stmt = select(
                RecoveryCase.failure_type,
                func.count(RecoveryCase.id),
                func.coalesce(func.sum(RecoveryCase.amount_paise), 0)
            ).join(
                PaymentEvent, PaymentEvent.recovery_case_id == RecoveryCase.id
            ).join(
                FunnelEvent, FunnelEvent.session_id == PaymentEvent.session_id
            ).where(
                FunnelEvent.event_type == FunnelEventType.PAYMENT_ATTEMPTED
            ).group_by(RecoveryCase.failure_type)

            rc_result = await db.execute(rc_stmt)
            for row in rc_result.all():
                root_causes.append(RootCauseBreakdown(
                    failure_type=row[0] if row[0] else "UNKNOWN",
                    count=row[1],
                    revenue_at_risk_paise=row[2]
                ))

            # Affected segment breakdown via multi-table join
            seg_stmt = select(
                Customer.segment,
                func.count(RecoveryCase.id)
            ).join(
                PaymentEvent, PaymentEvent.recovery_case_id == RecoveryCase.id
            ).join(
                FunnelEvent, FunnelEvent.session_id == PaymentEvent.session_id
            ).join(
                Customer, Customer.id == RecoveryCase.customer_id
            ).where(
                FunnelEvent.event_type == FunnelEventType.PAYMENT_ATTEMPTED
            ).group_by(Customer.segment)

            seg_result = await db.execute(seg_stmt)
            for row in seg_result.all():
                affected_segments.append(SegmentBreakdown(
                    segment=row[0].value if hasattr(row[0], 'value') else (row[0] if row[0] else "UNKNOWN"),
                    count=row[1]
                ))

            # Recovery actions summary via multi-table join
            ra_stmt = select(
                CandidateAction.action_type,
                func.count(CandidateAction.id),
                func.coalesce(func.sum(CandidateAction.expected_value_paise), 0)
            ).join(
                RecoveryCase, RecoveryCase.id == CandidateAction.case_id
            ).join(
                PaymentEvent, PaymentEvent.recovery_case_id == RecoveryCase.id
            ).join(
                FunnelEvent, FunnelEvent.session_id == PaymentEvent.session_id
            ).where(
                FunnelEvent.event_type == FunnelEventType.PAYMENT_ATTEMPTED
            ).group_by(CandidateAction.action_type)

            ra_result = await db.execute(ra_stmt)
            for row in ra_result.all():
                recovery_actions.append(RecoveryActionSummary(
                    action_type=row[0].value if hasattr(row[0], 'value') else str(row[0]),
                    count=row[1],
                    total_expected_recovery_paise=row[2]
                ))

        leaks.append(LeakPoint(
            from_stage=from_stage.stage,
            to_stage=to_stage.stage,
            lost_count=lost_count,
            lost_value_paise=lost_value,
            root_causes=root_causes,
            affected_segments=affected_segments,
            recovery_actions=recovery_actions
        ))

    return LeakGraphResponse(
        stages=stages,
        leaks=leaks,
        generated_at=datetime.now(UTC).isoformat()
    )
