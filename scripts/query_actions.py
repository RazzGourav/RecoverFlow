import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from apps.api.db.models import Action, ReconciliationRecord

DATABASE_URL = "postgresql+asyncpg://recoverflow:recoverflow@localhost:5432/recoverflow"

async def query_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine, class_=AsyncSession)
    
    async with Session() as session:
        # Get all actions and join with reconciliation
        result = await session.execute(
            select(Action, ReconciliationRecord)
            .join(ReconciliationRecord, Action.id == ReconciliationRecord.action_id, isouter=True)
            .order_by(Action.created_at.desc())
        )
        rows = result.all()
        
        print(f"{'Action Type':<25} | {'Execution Status':<20} | {'Reconciliation Status'}")
        print("-" * 75)
        for action, rec in rows:
            rec_status = rec.status.value if rec else "N/A"
            print(f"{action.action_type.value:<25} | {action.execution_status.value:<20} | {rec_status}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(query_db())
