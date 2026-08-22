import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Policy
from dependencies.db import get_db

router = APIRouter()

class PolicyUpdate(BaseModel):
    max_autonomous_amount_paise: int
    retry_limit: int
    cooldown_hours: int
    confidence_threshold: float
    human_review_threshold_paise: int

@router.get("/", response_model=dict[str, Any])
async def get_policy(db: AsyncSession = Depends(get_db)):
    """
    Get the global policy configuration.
    Since we are single-tenant for now, we just fetch the first policy.
    """
    stmt = select(Policy).limit(1)
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=404, detail="No policy found")

    return {
        "id": str(policy.id),
        "merchant_id": str(policy.merchant_id),
        "max_autonomous_amount_paise": policy.max_autonomous_amount_paise,
        "retry_limit": policy.retry_limit,
        "cooldown_hours": policy.cooldown_hours,
        "confidence_threshold": policy.confidence_threshold,
        "human_review_threshold_paise": policy.human_review_threshold_paise,
        "updated_at": policy.updated_at.isoformat()
    }

@router.put("/{policy_id}", response_model=dict[str, Any])
async def update_policy(policy_id: uuid.UUID, data: PolicyUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update the global policy configuration.
    """
    stmt = select(Policy).where(Policy.id == policy_id).with_for_update()
    result = await db.execute(stmt)
    policy = result.scalar_one_or_none()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.max_autonomous_amount_paise = data.max_autonomous_amount_paise
    policy.retry_limit = data.retry_limit
    policy.cooldown_hours = data.cooldown_hours
    policy.confidence_threshold = data.confidence_threshold
    policy.human_review_threshold_paise = data.human_review_threshold_paise

    await db.commit()

    return {
        "id": str(policy.id),
        "merchant_id": str(policy.merchant_id),
        "max_autonomous_amount_paise": policy.max_autonomous_amount_paise,
        "retry_limit": policy.retry_limit,
        "cooldown_hours": policy.cooldown_hours,
        "confidence_threshold": policy.confidence_threshold,
        "human_review_threshold_paise": policy.human_review_threshold_paise,
        "updated_at": policy.updated_at.isoformat()
    }
