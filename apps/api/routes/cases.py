import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db
from db.models import Action, AuthorizationStatus, ExecutionStatus
from pydantic import BaseModel

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
        await pool.enqueue_job("dispatch_action_job", action_id=str(action.id))
    else:
        # Fallback to creating a one-off connection
        from arq import create_pool
        from arq.connections import RedisSettings
        from config import settings
        try:
            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            await pool.enqueue_job("dispatch_action_job", action_id=str(action.id))
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
