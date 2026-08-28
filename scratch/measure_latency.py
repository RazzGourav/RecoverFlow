import time
import requests
import subprocess
import uuid

test_id = f"latency_{uuid.uuid4().hex[:8]}"

print(f"Triggering webhook with id: {test_id}...")

# Get initial latest case
try:
    resp = requests.get("http://localhost:8000/dashboard/feed")
    initial_cases = resp.json().get("recent_cases", [])
    initial_top_id = initial_cases[0]["id"] if initial_cases else None
except Exception as e:
    print(f"Error getting initial feed: {e}")
    initial_top_id = None

start_time = time.time()
# Fire webhook
subprocess.run(["python", "scripts/simulate_webhook.py", "--id", test_id, "--secret", "test_webhook_secret_123"], check=True)
webhook_fired_time = time.time()
print(f"Webhook fired in {webhook_fired_time - start_time:.2f}s. Polling dashboard...")

# Poll Dashboard
found = False
while time.time() - start_time < 30:
    try:
        resp = requests.get("http://localhost:8000/dashboard/feed")
        if resp.status_code == 200:
            data = resp.json()
            current_cases = data.get("recent_cases", [])
            current_top_id = current_cases[0]["id"] if current_cases else None
            
            if current_top_id != initial_top_id:
                latency = time.time() - webhook_fired_time
                print(f"Found new case in dashboard! Latency: {latency:.2f}s")
                found = True
                break
    except Exception as e:
        print(f"Error polling: {e}")
    time.sleep(0.1)

if not found:
    print("Timeout! Case never appeared in dashboard.")
