import asyncio
import time
import httpx

async def measure_latency():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Get baseline metric
        res = await client.get("/metrics")
        start_count = res.json().get("total_cases", 0)

        # Trigger webhook
        payload = {
            "entity": "event",
            "account_id": "acc_123",
            "event": "payment.failed",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_latency_{int(time.time())}",
                        "amount": 100000,
                        "currency": "INR",
                        "status": "failed",
                        "method": "card",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Latency test",
                        "error_source": "customer",
                        "error_step": "payment_initiation",
                        "error_reason": "payment_failed"
                    }
                }
            },
            "created_at": int(time.time())
        }
        
        t0 = time.perf_counter()
        # Fire webhook without waiting for it to process
        await client.post("/webhooks/razorpay", json=payload, headers={"x-razorpay-signature": "dummy"})
        
        # Poll DB/API until it shows up
        while True:
            res = await client.get("/metrics")
            if res.json().get("total_cases", 0) > start_count:
                t1 = time.perf_counter()
                print(f"End-to-End Latency: {t1 - t0:.3f} seconds")
                break
            await asyncio.sleep(0.05)

asyncio.run(measure_latency())
