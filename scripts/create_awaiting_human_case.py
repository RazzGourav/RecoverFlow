import asyncio
import uuid
import time
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings
from db.models import Action, ActionType, AuthorizationStatus, ExecutionStatus, RecoveryCase, CaseStatus, Customer, Merchant, CustomerSegment, FailureType

async def main():
    engine = create_async_engine(settings.database_sync_url.replace("postgresql://", "postgresql+asyncpg://").replace("postgres:5432", "localhost:5432"))
    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as db:
        # Get first merchant
        result = await db.execute(select(Merchant))
        merchant = result.scalars().first()
        if not merchant:
            print("No merchant found!")
            return
            
        # Get first customer
        result = await db.execute(select(Customer).where(Customer.merchant_id == merchant.id))
        customer = result.scalars().first()
        if not customer:
            print("No customer found!")
            return
            
        case = RecoveryCase(
            merchant_id=merchant.id,
            customer_id=customer.id,
            amount_paise=2600000, # 26000 INR, triggers human review threshold
            failure_type=FailureType.UNKNOWN,
            status=CaseStatus.AWAITING_APPROVAL,
            recoverability_score=0.85
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        
        action = Action(
            case_id=case.id,
            action_type=ActionType.PAYMENT_LINK,
            authorization_status=AuthorizationStatus.AWAITING_HUMAN,
            execution_status=ExecutionStatus.PENDING,
            idempotency_key=f"idem_{uuid.uuid4()}"
        )
        db.add(action)
        await db.commit()
        
        print(f"Created Case AWAITING_HUMAN: {case.id}")

if __name__ == "__main__":
    asyncio.run(main())
