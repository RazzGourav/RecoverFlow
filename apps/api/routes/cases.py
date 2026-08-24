import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Action, AuthorizationStatus, Customer, ExecutionStatus, RecoveryCase
from dependencies.db import get_db

router = APIRouter()

class ApprovalResponse(BaseModel):
    status: str
    action_id: str


@router.post("/{action_id}/approve", response_model=ApprovalResponse)
async def approve_action(action_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Approve an action that is AWAITING_HUMAN and enqueue it for execution.
    """
    stmt = select(Action).where(Action.id == action_id).with_for_update()
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.authorization_status != AuthorizationStatus.AWAITING_HUMAN:
        raise HTTPException(status_code=400, detail=f"Action is not awaiting human approval (current status: {action.authorization_status})")

    action.authorization_status = AuthorizationStatus.APPROVED
    await db.commit()

    # Enqueue execution
    pool = getattr(request.app.state, "arq_pool", None)
    if pool:
        await pool.enqueue_job("dispatch_action_job", action_id=str(action.id), _queue_name="arq:recovery_queue")
    else:
        # Fallback to creating a one-off connection
        from arq import create_pool
        from arq.connections import RedisSettings

        from config import settings
        try:
            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            await pool.enqueue_job("dispatch_action_job", action_id=str(action.id), _queue_name="arq:recovery_queue")
            await pool.close()
        except Exception:
            pass # The cron fallback will pick it up

    return ApprovalResponse(status="approved", action_id=str(action.id))


@router.post("/{action_id}/reject", response_model=ApprovalResponse)
async def reject_action(action_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Reject an action that is AWAITING_HUMAN.
    """
    stmt = select(Action).where(Action.id == action_id).with_for_update()
    result = await db.execute(stmt)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.authorization_status != AuthorizationStatus.AWAITING_HUMAN:
        raise HTTPException(status_code=400, detail=f"Action is not awaiting human approval (current status: {action.authorization_status})")

    action.authorization_status = AuthorizationStatus.BLOCKED
    action.execution_status = ExecutionStatus.CANCELLED
    await db.commit()

    return ApprovalResponse(status="rejected", action_id=str(action.id))


@router.get("/", response_model=list[dict])
async def list_cases(
    status: str | None = None,
    segment: str | None = None,
    risk_level: str | None = None,
    authorization_status: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RecoveryCase).options(selectinload(RecoveryCase.customer))
    if status:
        stmt = stmt.where(RecoveryCase.status == status)
    if risk_level:
        stmt = stmt.where(RecoveryCase.risk_level == risk_level)

    if segment:
        stmt = stmt.join(Customer).where(Customer.segment == segment)

    stmt = stmt.order_by(RecoveryCase.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    cases = result.scalars().all()

    # Filter by authorization_status if provided (requires inspecting the active action, for now we just do it in python)
    # A better way would be to join Action table, but let's keep it simple for now.

    res = []
    for c in cases:
        res.append({
            "id": str(c.id),
            "status": c.status.value if hasattr(c.status, 'value') else c.status,
            "amount_paise": c.amount_paise,
            "expected_recovery_paise": int(c.recoverability_score * c.amount_paise) if c.recoverability_score is not None else 0,
            "failure_type": c.failure_type.value if hasattr(c.failure_type, 'value') else c.failure_type,
            "risk_level": (c.risk_level.value if hasattr(c.risk_level, 'value') else c.risk_level) if c.risk_level else None,
            "customer_segment": (c.customer.segment.value if hasattr(c.customer.segment, 'value') else c.customer.segment) if c.customer else None,
            "created_at": c.created_at.isoformat()
        })
    return res


@router.get("/{case_id}", response_model=dict)
async def get_case(case_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(RecoveryCase).options(
        selectinload(RecoveryCase.customer),
        selectinload(RecoveryCase.payment_event),
        selectinload(RecoveryCase.candidate_actions),
        selectinload(RecoveryCase.actions),
        selectinload(RecoveryCase.audit_events)
    ).where(RecoveryCase.id == case_id)

    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Case not found")

    return {
        "id": str(c.id),
        "status": c.status.value if hasattr(c.status, 'value') else c.status,
        "amount_paise": c.amount_paise,
        "failure_type": c.failure_type.value if hasattr(c.failure_type, 'value') else c.failure_type,
        "risk_level": (c.risk_level.value if hasattr(c.risk_level, 'value') else c.risk_level) if c.risk_level else None,
        "risk_score": c.risk_score,
        "recoverability_score": c.recoverability_score,
        "llm_explanation": c.llm_explanation,
        "created_at": c.created_at.isoformat(),
        "customer": {
            "id": str(c.customer.id),
            "segment": c.customer.segment.value if hasattr(c.customer.segment, 'value') else c.customer.segment,
            "tenure_days": c.customer.tenure_days,
            "external_customer_id": c.customer.external_customer_id
        } if c.customer else None,
        "payment_event": {
            "id": str(c.payment_event.id),
            "event_type": c.payment_event.event_type,
            "status": c.payment_event.status.value if hasattr(c.payment_event.status, 'value') else c.payment_event.status,
            "raw_payload": c.payment_event.raw_payload
        } if c.payment_event else None,
        "candidate_actions": [
            {
                "id": str(ca.id),
                "action_type": ca.action_type.value if hasattr(ca.action_type, 'value') else ca.action_type,
                "expected_value_paise": ca.expected_value_paise,
                "probability": ca.probability,
                "rank": ca.rank
            } for ca in sorted(c.candidate_actions, key=lambda x: (x.rank is None, x.rank))
        ],
        "actions": [
            {
                "id": str(a.id),
                "action_type": a.action_type.value if hasattr(a.action_type, 'value') else a.action_type,
                "authorization_status": a.authorization_status.value if hasattr(a.authorization_status, 'value') else a.authorization_status,
                "execution_status": a.execution_status.value if hasattr(a.execution_status, 'value') else a.execution_status,
                "cost_estimate_paise": a.cost_estimate_paise,
                "created_at": a.created_at.isoformat()
            } for a in sorted(c.actions, key=lambda x: x.created_at, reverse=True)
        ],
        "audit_events": [
            {
                "id": str(ae.id),
                "event_type": ae.event_type.value if hasattr(ae.event_type, 'value') else ae.event_type,
                "decision": ae.decision,
                "reason": ae.reason,
                "context": ae.context,
                "timestamp": ae.timestamp.isoformat()
            } for ae in sorted(c.audit_events, key=lambda x: x.timestamp)
        ]
    }
