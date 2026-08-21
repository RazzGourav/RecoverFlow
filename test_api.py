import urllib.request
import json
import time

def test_endpoint(name, url):
    print(f"\n--- Testing {name} ---")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"SUCCESS ({response.status})")
            if isinstance(data, list):
                print(f"Returned list with {len(data)} items")
            elif isinstance(data, dict):
                print(f"Returned dict with keys: {list(data.keys())}")
            else:
                print("Returned:", type(data))
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    time.sleep(10) # wait for API to be up
    base = "http://localhost:8000"
    test_endpoint("dashboard/feed", f"{base}/dashboard/feed")
    test_endpoint("cases", f"{base}/cases")
    test_endpoint("policies", f"{base}/policies")
    test_endpoint("audit", f"{base}/audit")
