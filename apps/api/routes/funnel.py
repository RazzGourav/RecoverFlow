"""
RecoverFlow API — Funnel Ingestion & Aggregation
"""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from integrations.analytics.synthetic import SyntheticProvider
from integrations.analytics.base import FunnelSummaryNode


router = APIRouter()


class TrackEventRequest(BaseModel):
    session_id: str
    event_type: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrackEventResponse(BaseModel):
    status: str
    message: str


class FunnelSummaryResponse(BaseModel):
    nodes: List[FunnelSummaryNode]
    note: str = "Simulated traffic data: top-of-funnel events (visits/views/cart) are synthetically generated."


@router.post("/events/track", response_model=TrackEventResponse, status_code=201)
async def track_event(request: TrackEventRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingest a funnel tracking event from an analytics SDK or simulation script.
    Idempotent by (session_id, event_type, timestamp).
    """
    provider = SyntheticProvider(db)
    try:
        await provider.track_event(
            session_id=request.session_id,
            event_type=request.event_type,
            timestamp=request.timestamp,
            metadata=request.metadata
        )
        return TrackEventResponse(status="success", message="Event tracked")
    except ValueError as e:
        # Invalid enum or UUID format
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary", response_model=FunnelSummaryResponse)
async def get_summary(db: AsyncSession = Depends(get_db)):
    """
    Aggregates the funnel stages and computes drop-off rates from DB.
    """
    provider = SyntheticProvider(db)
    nodes = await provider.get_funnel_summary()
    return FunnelSummaryResponse(nodes=nodes)
