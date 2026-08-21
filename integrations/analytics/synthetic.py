import uuid
import structlog
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

try:
    from db.models import Session, FunnelEvent, FunnelEventType
except ImportError:
    from apps.api.db.models import Session, FunnelEvent, FunnelEventType
from integrations.analytics.base import EventTrackingProvider, FunnelSummaryNode

logger = structlog.get_logger(__name__)

class SyntheticProvider(EventTrackingProvider):
    """
    Local database implementation of the EventTrackingProvider.
    Ingests synthetic session events into the local Postgres tables.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def track_event(
        self,
        session_id: str,
        event_type: str,
        timestamp: datetime,
        metadata: Dict[str, Any]
    ) -> None:
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise ValueError(f"Invalid session_id format: {session_id}")

        try:
            enum_type = FunnelEventType[event_type]
        except KeyError:
            raise ValueError(f"Unsupported event_type: {event_type}")

        # Ensure session exists (create if not)
        stmt = select(Session).where(Session.id == session_uuid)
        result = await self.db.execute(stmt)
        session_obj = result.scalar_one_or_none()
        
        if not session_obj:
            session_obj = Session(id=session_uuid, started_at=timestamp, metadata_=metadata)
            self.db.add(session_obj)
            try:
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                # Race condition handled

        # Check idempotency on (session_id, event_type, timestamp)
        # Note: timestamp might differ slightly in float precision if not careful, 
        # but exact match is required for idempotency here.
        event_stmt = select(FunnelEvent).where(
            FunnelEvent.session_id == session_uuid,
            FunnelEvent.event_type == enum_type,
            FunnelEvent.timestamp == timestamp
        )
        event_result = await self.db.execute(event_stmt)
        existing_event = event_result.scalar_one_or_none()

        if existing_event:
            logger.info("analytics.track_event.duplicate_ignored", session_id=session_id, event_type=event_type)
            return

        product_id = metadata.get("product_id")
        cart_value = metadata.get("cart_value_paise")
        
        new_event = FunnelEvent(
            session_id=session_uuid,
            event_type=enum_type,
            timestamp=timestamp,
            product_id=product_id,
            cart_value_paise=cart_value
        )
        self.db.add(new_event)
        await self.db.commit()
        logger.info("analytics.track_event.success", session_id=session_id, event_type=event_type)


    async def get_funnel_summary(self) -> List[FunnelSummaryNode]:
        # Group by event_type
        stmt = select(
            FunnelEvent.event_type,
            func.count(FunnelEvent.id),
            func.sum(FunnelEvent.cart_value_paise)
        ).group_by(FunnelEvent.event_type)
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        stats = {row[0]: {"count": row[1], "value": row[2] or 0} for row in rows}
        
        # Define funnel order
        order = [
            FunnelEventType.SITE_VISIT,
            FunnelEventType.PRODUCT_VIEW,
            FunnelEventType.ADD_TO_CART,
            FunnelEventType.CHECKOUT_STARTED,
            FunnelEventType.PAYMENT_ATTEMPTED
        ]
        
        nodes = []
        prev_count = None
        
        for stage in order:
            count = stats.get(stage, {}).get("count", 0)
            value = stats.get(stage, {}).get("value", 0)
            
            dropoff = None
            if prev_count is not None and prev_count > 0:
                dropoff = ((prev_count - count) / prev_count) * 100.0
                
            nodes.append(FunnelSummaryNode(
                stage=stage.value,
                count=count,
                dropoff_rate_percent=dropoff,
                value_paise=value
            ))
            
            prev_count = count
            
        return nodes
