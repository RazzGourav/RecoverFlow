#!/usr/bin/env python3
"""
RecoverFlow — Funnel Data Seeder

Why: The leak_graph endpoint reads from funnel_events which is empty after a
fresh container start. This script seeds a realistic funnel with deterministic
drop-offs so the Leak Graph visualization has meaningful data on demo day.

Deterministic (fixed seed=42) so re-running produces identical results.

Usage (from repo root, inside Docker):
    docker compose exec api python scripts/seed_funnel_data.py
"""

import asyncio
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Make models importable
root_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_dir / "apps" / "api"))
sys.path.insert(0, str(root_dir))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from db.models import FunnelEvent, FunnelEventType
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Config — reproducible with fixed seed
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
NUM_TOP_SESSIONS = 200  # site-visit sessions to simulate

# Realistic funnel conversion probabilities
STAGE_PROBS = [
    (FunnelEventType.SITE_VISIT, 1.00),
    (FunnelEventType.PRODUCT_VIEW, 0.62),
    (FunnelEventType.ADD_TO_CART, 0.45),
    (FunnelEventType.CHECKOUT_STARTED, 0.58),
    (FunnelEventType.PAYMENT_ATTEMPTED, 0.78),
]


async def seed_funnel() -> None:
    """Insert deterministic funnel events to power the Leak Graph."""
    rng = random.Random(RANDOM_SEED)

    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        inserted = 0
        base_time = datetime.now(UTC) - timedelta(hours=6)

        for i in range(NUM_TOP_SESSIONS):
            session_id = uuid.uuid4()
            cart_value = rng.randint(50_000, 2_000_000)  # ₹500 – ₹20,000 in paise
            product_id = f"prod_{rng.randint(1, 50)}"
            session_start = base_time + timedelta(seconds=i * 30)

            # sessions table must exist for FK on funnel_events.session_id
            await session.execute(
                text("INSERT INTO sessions (id, started_at, metadata) VALUES (:id, :started_at, :meta)"),
                {"id": session_id, "started_at": session_start, "meta": "{}"},
            )

            for stage, prob in STAGE_PROBS:
                if rng.random() > prob:
                    break  # user dropped off

                fe = FunnelEvent(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    event_type=stage,
                    timestamp=session_start,
                    cart_value_paise=cart_value if stage != FunnelEventType.SITE_VISIT else None,
                    product_id=product_id if stage != FunnelEventType.SITE_VISIT else None,
                )
                session.add(fe)
                inserted += 1
                session_start += timedelta(seconds=rng.randint(5, 120))

        await session.commit()
        print(f"✅ Seeded {inserted} funnel events from {NUM_TOP_SESSIONS} simulated sessions.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_funnel())
