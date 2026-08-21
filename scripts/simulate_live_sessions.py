#!/usr/bin/env python3
"""
Live-Fire Funnel Simulator

Fires synthetic funnel events in real time to the RecoverFlow API.
Useful for demonstrating live dashboard updates.

Usage:
  python scripts/simulate_live_sessions.py [--rate 1.0]

Where --rate is the base sleep time (seconds) between global ticks.
"""

import asyncio
import uuid
import random
import argparse
from datetime import datetime, timezone
import httpx

API_URL = "http://localhost:8000/funnel/events/track"

# Funnel drop-offs matching the dataset-card assumptions
# VISIT (100) -> VIEW (40) -> CART (35) -> CHECKOUT (60) -> PAYMENT (72)
FUNNEL_STAGES = [
    ("SITE_VISIT", 1.0),
    ("PRODUCT_VIEW", 0.40),
    ("ADD_TO_CART", 0.35),
    ("CHECKOUT_STARTED", 0.60),
    ("PAYMENT_ATTEMPTED", 0.72)
]

async def simulate_session(client: httpx.AsyncClient):
    session_id = str(uuid.uuid4())
    metadata = {"source": random.choice(["organic", "paid", "direct", "referral"])}
    cart_value = random.randint(50000, 500000)
    product_id = f"prod_{random.randint(1, 100)}"
    
    print(f"[{session_id}] Started session")
    
    for stage, prob in FUNNEL_STAGES:
        if random.random() > prob:
            print(f"[{session_id}] Dropped off before {stage}")
            break
            
        payload = {
            "session_id": session_id,
            "event_type": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata.copy()
        }
        
        if stage in ("PRODUCT_VIEW", "ADD_TO_CART", "CHECKOUT_STARTED", "PAYMENT_ATTEMPTED"):
            payload["metadata"]["product_id"] = product_id
            
        if stage in ("ADD_TO_CART", "CHECKOUT_STARTED", "PAYMENT_ATTEMPTED"):
            payload["metadata"]["cart_value_paise"] = cart_value
            
        try:
            resp = await client.post(API_URL, json=payload, timeout=5.0)
            if resp.status_code == 201:
                print(f"[{session_id}] -> {stage} tracked")
            else:
                print(f"[{session_id}] -> {stage} failed: {resp.text}")
        except Exception as e:
            print(f"[{session_id}] Error: {str(e)}")
            
        # Realistic pause between stages
        await asyncio.sleep(random.uniform(0.5, 3.0))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=1.0, help="Seconds to wait before spawning a new session")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N sessions (0 = infinite)")
    args = parser.parse_args()
    
    print(f"Starting live-fire simulator targeting {API_URL}")
    print(f"Spawning 1 session roughly every {args.rate}s...")
    
    async with httpx.AsyncClient() as client:
        spawned = 0
        tasks = set()
        
        try:
            while True:
                if args.limit > 0 and spawned >= args.limit:
                    break
                    
                task = asyncio.create_task(simulate_session(client))
                tasks.add(task)
                task.add_done_callback(tasks.discard)
                
                spawned += 1
                await asyncio.sleep(args.rate * random.uniform(0.5, 1.5))
                
            # Wait for remaining tasks
            if tasks:
                await asyncio.gather(*tasks)
                
        except KeyboardInterrupt:
            print("\nStopping simulation.")

if __name__ == "__main__":
    asyncio.run(main())
