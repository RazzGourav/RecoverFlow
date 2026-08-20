#!/usr/bin/env python3
"""
RecoverFlow — Database Seeder

Why this file exists:
  Loads a small slice of synthetic dataset into the local PostgreSQL database
  so that the local development and demo environments start from a known,
  realistic state. It wipes existing cases to ensure idempotency when called
  multiple times.
"""

import asyncio
import csv
import json
import os
import random
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup path so we can import from apps.api
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from config import settings
from db.models import (
    Merchant, Customer, Subscription, PaymentEvent, RecoveryCase, CandidateAction,
    CustomerSegment, FailureType, PaymentEventStatus, ActionType, Base
)

PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
TRAIN_CSV = PROCESSED_DIR / "train.csv"


async def clear_database(session: AsyncSession):
    """Clear existing cases and dependencies so seed is idempotent."""
    await session.execute(delete(CandidateAction))
    await session.execute(delete(RecoveryCase))
    await session.execute(delete(PaymentEvent))
    await session.execute(delete(Subscription))
    await session.execute(delete(Customer))
    await session.execute(delete(Merchant))
    await session.commit()
    print("Cleaned existing data.")


async def seed():
    if not TRAIN_CSV.exists():
        print("synthetic data not found. Run generate.py first.")
        return

    # Create the Async engine
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        await clear_database(session)

        # 1. Create a dummy merchant
        merchant = Merchant(name="Demo Merchant Ltd.")
        session.add(merchant)
        await session.flush()

        # 2. Read first 50 rows from train.csv
        rows = []
        with open(TRAIN_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= 50:
                    break
                rows.append(row)

        print(f"Loading {len(rows)} cases...")

        for row in rows:
            # 3. Create Customer
            segment = CustomerSegment(row["segment"])
            tenure_days = int(row["tenure_days"])
            
            customer = Customer(
                merchant_id=merchant.id,
                segment=segment,
                tenure_days=tenure_days
            )
            session.add(customer)
            await session.flush()

            # 4. Create Subscription
            amount_paise = int(row["amount_paise"])
            sub = Subscription(
                customer_id=customer.id,
                plan_id="plan_demo",
                amount_paise=amount_paise
            )
            session.add(sub)
            await session.flush()

            # 5. Create PaymentEvent
            failure_type = FailureType(row["failure_type"])
            ext_id = row["external_event_id"]
            # A bit of a hack: if is_duplicate is 'True', we'll just skip creating a duplicate in the seed for now,
            # or handle it nicely.
            if row["is_duplicate"] == "True":
                continue

            event = PaymentEvent(
                external_event_id=ext_id,
                event_type="payment.failed",
                payload_hash="dummy_hash",
                raw_payload={"event": "payment.failed"},
                status=PaymentEventStatus.PROCESSED
            )
            session.add(event)
            await session.flush()

            # 6. Create RecoveryCase
            actually_recovered = row["actually_recovered"] == "True"
            case = RecoveryCase(
                payment_event_id=event.id,
                subscription_id=sub.id,
                customer_id=customer.id,
                merchant_id=merchant.id,
                amount_paise=amount_paise,
                failure_type=failure_type
            )
            session.add(case)
            await session.flush()

            event.recovery_case_id = case.id

            # 7. Create CandidateAction (just picking the one it took as the top candidate)
            action_type = ActionType(row["action_taken"])
            cand = CandidateAction(
                case_id=case.id,
                action_type=action_type,
                success_probability=0.75 if actually_recovered else 0.25,
                expected_value_paise=amount_paise,
                rank=1
            )
            session.add(cand)

        await session.commit()
        print("✅ Database seeded successfully for local dev.")


if __name__ == "__main__":
    asyncio.run(seed())
