import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport, AsyncClient

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from apps.api.db.models import Action, AuditEvent, ExecutionStatus, RecoveryCase, CaseStatus

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
async def test_simulation_read_only_guarantee(db_engine_and_session):
    """
    Verifies that running a simulation does NOT result in any permanent writes to Action or AuditEvent.
    """
    engine, Session = db_engine_and_session
    async with Session() as db_session:
        # Count before
        actions_before = (await db_session.execute(select(func.count(Action.id)))).scalar()
        audits_before = (await db_session.execute(select(func.count(AuditEvent.id)))).scalar()

        # Import and run core simulator
        from ai.evaluation.simulation_core import simulate_strategy_batch
        
        # We need a case in OPEN status
        case_ids = []
        stmt = select(RecoveryCase.id).where(RecoveryCase.status == CaseStatus.OPEN).limit(10)
        res = await db_session.execute(stmt)
        case_ids = list(res.scalars().all())
        
        if not case_ids:
            pytest.skip("No open cases available for simulation test.")

        result = await simulate_strategy_batch(
            session=db_session,
            case_ids=case_ids,
            strategy="RECOVERFLOW_OPTIMAL",
            budget_paise=500000
        )
        
        assert result.cases_processed == len(case_ids)

        # Count after
        actions_after = (await db_session.execute(select(func.count(Action.id)))).scalar()
        audits_after = (await db_session.execute(select(func.count(AuditEvent.id)))).scalar()

        assert actions_before == actions_after, "Simulation leaked Action rows to DB"
        assert audits_before == audits_after, "Simulation leaked AuditEvent rows to DB"


@pytest.mark.asyncio
async def test_simulate_compare_endpoint(async_client: AsyncClient, db_engine_and_session):
    """
    Verifies the POST /simulate/compare endpoint returns the correct comparison matrix
    and completes within the performance budget.
    """
    import time
    
    start_time = time.time()
    response = await async_client.post("/simulate/compare", json={"sample_size": 10, "budget_paise": 500000})
    duration = time.time() - start_time
    
    # Check if there are no cases
    if response.status_code == 400:
        pytest.skip("No open cases available for simulation test.")
        
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    
    results = data["results"]
    assert len(results) == 6  # 6 strategies defined
    
    strategies = [r["strategy"] for r in results]
    assert "RECOVERFLOW_OPTIMAL" in strategies
    assert "DO_NOTHING" in strategies
    
    # Performance check: 10 cases * 6 strategies should be fast
    assert duration < 5.0, f"Simulation took too long: {duration}s"
