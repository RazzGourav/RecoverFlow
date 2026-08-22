import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport, AsyncClient

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.api.db.models import Action, AuditEvent, RecoveryCase, CaseStatus

TEST_DATABASE_URL = "postgresql+asyncpg://recoverflow:recoverflow@localhost:5432/recoverflow"

@pytest_asyncio.fixture
async def db_engine_and_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    TestingSessionLocal = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield test_engine, TestingSessionLocal
    await test_engine.dispose()

@pytest_asyncio.fixture
async def async_client():
    from apps.api.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

@pytest.mark.asyncio
async def test_replay_read_only_guarantee(async_client: AsyncClient, db_engine_and_session):
    """
    Verifies that calling POST /simulate/replay/{case_id} does NOT result in any permanent writes to Action or AuditEvent.
    """
    engine, Session = db_engine_and_session
    
    case_id = None
    
    async with Session() as db_session:
        # Count before
        actions_before = (await db_session.execute(select(func.count(Action.id)))).scalar()
        audits_before = (await db_session.execute(select(func.count(AuditEvent.id)))).scalar()
        
        # We need a case in OPEN status
        stmt = select(RecoveryCase.id).where(RecoveryCase.status == CaseStatus.OPEN).limit(1)
        res = await db_session.execute(stmt)
        case_id = res.scalar_one_or_none()

    if not case_id:
        pytest.skip("No open cases available for replay test.")

    # Call replay endpoint
    response = await async_client.post(
        f"/simulate/replay/{case_id}", 
        json={"strategy": "RECOVERFLOW_OPTIMAL"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "timeline" in data
    assert "before" in data
    assert "after" in data

    async with Session() as db_session:
        # Count after
        actions_after = (await db_session.execute(select(func.count(Action.id)))).scalar()
        audits_after = (await db_session.execute(select(func.count(AuditEvent.id)))).scalar()

        assert actions_before == actions_after, "Replay leaked Action rows to DB"
        assert audits_before == audits_after, "Replay leaked AuditEvent rows to DB"
