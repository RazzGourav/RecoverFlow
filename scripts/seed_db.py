#!/usr/bin/env python3
"""
RecoverFlow — Database Seeder

Why this file exists:
  Loads a small slice of synthetic dataset into the local PostgreSQL database
  so that the local development and demo environments start from a known,
  realistic state. It wipes existing cases to ensure idempotency when called
  multiple times.

  CandidateAction rows use real ML-model probabilities (not hardcoded labels).
"""

import asyncio
import csv

# Setup path so we can import from apps.api
import sys
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "apps" / "api"))
sys.path.insert(0, str(root_dir))

from config import settings
from db.models import (
    ActionType,
    CandidateAction,
    Customer,
    CustomerSegment,
    FailureType,
    Merchant,
    PaymentEvent,
    PaymentEventStatus,
    RecoveryCase,
    Subscription,
)

PROCESSED_DIR = root_dir / "data" / "processed"
TRAIN_CSV = PROCESSED_DIR / "train.csv"


def _compute_real_success_probability(row: dict) -> float:
    """Compute the intervention model's predicted success probability.

    Uses the same feature engineering + model path as the live inference
    engine (ai/inference/predict.py), eliminating all hardcoded labels.
    """
    import pandas as pd
    from ai.features.engineer import ACTION_TYPES, build_features
    from ai.inference import predict

    predict.load_models()

    case_data = {
        "amount_paise": int(row["amount_paise"]),
        "failure_type": row["failure_type"],
        "segment": row["segment"],
        "tenure_days": int(row["tenure_days"]),
    }
    df = pd.DataFrame([case_data])
    X_base = build_features(df)

    action = row["action_taken"]
    X_action = X_base.copy()
    for a in ACTION_TYPES:
        X_action[f"action_{a}"] = 1 if a == action else 0

    prob = float(predict._intervention_model.predict_proba(X_action)[0, 1])
    return prob


async def clear_database(session: AsyncSession) -> None:
    """Clear existing cases and dependencies so seed is idempotent."""
    await session.execute(delete(CandidateAction))
    await session.execute(delete(RecoveryCase))
    await session.execute(delete(PaymentEvent))
    await session.execute(delete(Subscription))
    await session.execute(delete(Customer))
    await session.execute(delete(Merchant))
    await session.commit()
    print("Cleaned existing data.")


async def seed() -> None:
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
        rows: list[dict] = []
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
            # Skip duplicates — they're for ML training, not DB seeding
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

            # 7. Create CandidateAction — real ML probability, not hardcoded
            action_type = ActionType(row["action_taken"])
            real_prob = _compute_real_success_probability(row)
            cand = CandidateAction(
                case_id=case.id,
                action_type=action_type,
                success_probability=real_prob,
                expected_value_paise=int(amount_paise * real_prob),
                rank=1
            )
            session.add(cand)

        await session.commit()
        print("✅ Database seeded successfully for local dev.")


if __name__ == "__main__":
    asyncio.run(seed())

