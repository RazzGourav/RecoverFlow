import uuid
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy import select, func

from apps.api.db.models import FunnelEvent, FunnelEventType, Session


@pytest.mark.asyncio
async def test_leak_graph_consistency(db_session, test_app):
    """
    Verify that leak-graph stage counts match direct DB counts —
    no drift between the aggregation endpoint and raw data.
    """
    # Seed some funnel data
    session_id_1 = uuid.uuid4()
    session_id_2 = uuid.uuid4()
    session_id_3 = uuid.uuid4()

    for sid in [session_id_1, session_id_2, session_id_3]:
        db_session.add(Session(id=sid, started_at=datetime.now(timezone.utc)))
    
    # 3 visits, 2 product views, 1 add to cart
    db_session.add(FunnelEvent(session_id=session_id_1, event_type=FunnelEventType.SITE_VISIT))
    db_session.add(FunnelEvent(session_id=session_id_2, event_type=FunnelEventType.SITE_VISIT))
    db_session.add(FunnelEvent(session_id=session_id_3, event_type=FunnelEventType.SITE_VISIT))
    db_session.add(FunnelEvent(session_id=session_id_1, event_type=FunnelEventType.PRODUCT_VIEW))
    db_session.add(FunnelEvent(session_id=session_id_2, event_type=FunnelEventType.PRODUCT_VIEW))
    db_session.add(FunnelEvent(
        session_id=session_id_1, event_type=FunnelEventType.ADD_TO_CART,
        cart_value_paise=100000
    ))
    await db_session.commit()

    # Direct DB count
    visit_count_stmt = select(func.count(FunnelEvent.id)).where(
        FunnelEvent.event_type == FunnelEventType.SITE_VISIT
    )
    visit_count = (await db_session.execute(visit_count_stmt)).scalar()
    assert visit_count == 3

    # API response
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        resp = await client.get("/leak-graph")
        assert resp.status_code == 200
        data = resp.json()

    # Find SITE_VISIT stage in response
    site_visit_stage = next(s for s in data["stages"] if s["stage"] == "SITE_VISIT")
    assert site_visit_stage["count"] == visit_count  # Must match DB

    # Find PRODUCT_VIEW
    pv_stage = next(s for s in data["stages"] if s["stage"] == "PRODUCT_VIEW")
    assert pv_stage["count"] == 2

    # Verify leaks exist
    assert len(data["leaks"]) > 0
    
    # First leak: SITE_VISIT -> PRODUCT_VIEW should show 1 lost
    first_leak = next(l for l in data["leaks"] if l["from_stage"] == "SITE_VISIT")
    assert first_leak["lost_count"] == 1  # 3 visits - 2 views

    # Verify honesty note is present
    assert "simulated" in data["note"].lower() or "Simulated" in data["note"]
