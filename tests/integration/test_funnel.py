import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select

from apps.api.db.models import FunnelEvent, FunnelEventType, Session


@pytest.mark.asyncio
async def test_funnel_ingestion_idempotency(db_session, test_app):
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "session_id": session_id,
        "event_type": "SITE_VISIT",
        "timestamp": now,
        "metadata": {"source": "test"}
    }
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        # First call should create session and event
        resp1 = await client.post("/funnel/events/track", json=payload)
        assert resp1.status_code == 201
        
        # Second call should be ignored (idempotent)
        resp2 = await client.post("/funnel/events/track", json=payload)
        assert resp2.status_code == 201
        
    # Verify exactly one event was created
    stmt = select(FunnelEvent).where(
        FunnelEvent.session_id == uuid.UUID(session_id),
        FunnelEvent.event_type == FunnelEventType.SITE_VISIT
    )
    result = await db_session.execute(stmt)
    events = result.scalars().all()
    
    assert len(events) == 1
    
    # Verify session was created
    stmt = select(Session).where(Session.id == uuid.UUID(session_id))
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_funnel_summary_aggregation(db_session, test_app):
    # Setup some deterministic data
    session_id_1 = uuid.uuid4()
    session_id_2 = uuid.uuid4()
    
    s1 = Session(id=session_id_1, started_at=datetime.now(timezone.utc))
    s2 = Session(id=session_id_2, started_at=datetime.now(timezone.utc))
    db_session.add_all([s1, s2])
    
    # 2 SITE_VISITs, 1 PRODUCT_VIEW
    db_session.add(FunnelEvent(session_id=session_id_1, event_type=FunnelEventType.SITE_VISIT))
    db_session.add(FunnelEvent(session_id=session_id_2, event_type=FunnelEventType.SITE_VISIT))
    db_session.add(FunnelEvent(session_id=session_id_1, event_type=FunnelEventType.PRODUCT_VIEW, cart_value_paise=0))
    await db_session.commit()
    
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        resp = await client.get("/funnel/summary")
        assert resp.status_code == 200
        data = resp.json()
        
    nodes = data["nodes"]
    assert len(nodes) == 5 # 5 stages total
    
    visit_node = next(n for n in nodes if n["stage"] == "SITE_VISIT")
    assert visit_node["count"] == 2
    assert visit_node["dropoff_rate_percent"] is None
    
    view_node = next(n for n in nodes if n["stage"] == "PRODUCT_VIEW")
    assert view_node["count"] == 1
    assert view_node["dropoff_rate_percent"] == 50.0 # (2 - 1) / 2 = 50%
