"""
Generates top-of-funnel synthetic traffic to model revenue leak before the payment stage.

Assumed Drop-off Rates:
- SITE_VISIT -> PRODUCT_VIEW: 40% conversion
- PRODUCT_VIEW -> ADD_TO_CART: 35% conversion
- ADD_TO_CART -> CHECKOUT_STARTED: 60% conversion
- CHECKOUT_STARTED -> PAYMENT_ATTEMPTED: 72% conversion

This script runs against the local DB, generates deterministic sessions, and explicitly links 
the final PAYMENT_ATTEMPTED stage back to existing `payment_events` rows to bridge the datasets.
"""

import sys
import uuid
import random
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_db, async_session_maker
from db.models import Session, FunnelEvent, FunnelEventType, PaymentEvent

SEED = 42

async def generate_funnel_data():
    random.seed(SEED)
    print(f"Generating synthetic funnel data with seed {SEED}...")
    
    async with async_session_maker() as db:
        # Fetch up to 1000 existing payment events that don't have a session linked yet
        stmt = select(PaymentEvent).where(PaymentEvent.session_id.is_(None)).limit(1000)
        result = await db.execute(stmt)
        unlinked_payments = result.scalars().all()
        
        target_payment_count = len(unlinked_payments)
        print(f"Found {target_payment_count} unlinked payment events. Will generate funnel to cover these.")
        
        if target_payment_count == 0:
            print("No unlinked payments found. Run the Phase 2 generator first.")
            return

        # Reverse engineer how many site visits we need to get `target_payment_count` payment attempts.
        # Product of conversion rates: 0.40 * 0.35 * 0.60 * 0.72 ≈ 0.06048 (approx 6%)
        # So we need target_payment_count / 0.06 total sessions.
        total_sessions = int(target_payment_count / 0.06048)
        print(f"Generating {total_sessions} total sessions to achieve expected conversion rates.")
        
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        payment_index = 0
        
        # Batching for performance
        sessions_to_add = []
        events_to_add = []
        payments_to_update = []
        
        for i in range(total_sessions):
            session_id = uuid.uuid4()
            # Spread sessions over the last 30 days
            started_at = base_time + timedelta(minutes=random.randint(0, 30 * 24 * 60))
            
            s = Session(id=session_id, started_at=started_at, metadata_={"source": random.choice(["organic", "paid", "direct", "referral"])})
            sessions_to_add.append(s)
            
            current_time = started_at
            
            # Stage 1: SITE_VISIT (100% of sessions)
            events_to_add.append(FunnelEvent(
                session_id=session_id, event_type=FunnelEventType.SITE_VISIT, timestamp=current_time
            ))
            
            # Stage 2: PRODUCT_VIEW (40%)
            if random.random() <= 0.40:
                current_time += timedelta(seconds=random.randint(10, 120))
                events_to_add.append(FunnelEvent(
                    session_id=session_id, event_type=FunnelEventType.PRODUCT_VIEW, timestamp=current_time,
                    product_id=f"prod_{random.randint(1, 100)}"
                ))
                
                # Stage 3: ADD_TO_CART (35%)
                if random.random() <= 0.35:
                    current_time += timedelta(seconds=random.randint(30, 300))
                    cart_value = random.randint(50000, 500000) # 500 to 5000 INR
                    events_to_add.append(FunnelEvent(
                        session_id=session_id, event_type=FunnelEventType.ADD_TO_CART, timestamp=current_time,
                        cart_value_paise=cart_value
                    ))
                    
                    # Stage 4: CHECKOUT_STARTED (60%)
                    if random.random() <= 0.60:
                        current_time += timedelta(seconds=random.randint(15, 60))
                        events_to_add.append(FunnelEvent(
                            session_id=session_id, event_type=FunnelEventType.CHECKOUT_STARTED, timestamp=current_time,
                            cart_value_paise=cart_value
                        ))
                        
                        # Stage 5: PAYMENT_ATTEMPTED (72%)
                        # Also, if we still have unlinked payments, we force link one.
                        if random.random() <= 0.72 or (total_sessions - i) <= (target_payment_count - payment_index):
                            if payment_index < target_payment_count:
                                current_time += timedelta(seconds=random.randint(30, 120))
                                payment_evt = unlinked_payments[payment_index]
                                
                                events_to_add.append(FunnelEvent(
                                    session_id=session_id, event_type=FunnelEventType.PAYMENT_ATTEMPTED, timestamp=current_time,
                                    cart_value_paise=cart_value # Ideally matches payment_evt amount, but fine for synthetic mapping
                                ))
                                
                                # Link back
                                payment_evt.session_id = session_id
                                payments_to_update.append(payment_evt)
                                payment_index += 1
                                
        db.add_all(sessions_to_add)
        db.add_all(events_to_add)
        # SQLAlchemy tracks the modified unlinked_payments automatically, but we can explicitly add if detached.
        
        await db.commit()
        print(f"Generated {len(sessions_to_add)} sessions and {len(events_to_add)} funnel events.")
        print(f"Successfully linked {payment_index} payment events to funnel sessions.")

if __name__ == "__main__":
    asyncio.run(generate_funnel_data())
