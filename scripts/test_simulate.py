#!/usr/bin/env python3
"""Quick smoke test for simulate/compare endpoint.

Run with:
  docker exec recoverflow-api python3 /scripts/test_simulate.py
"""
import urllib.request
import json

url = "http://localhost:8000/simulate/compare"
payload = json.dumps({"sample_size": 3}).encode()
req = urllib.request.Request(url, data=payload, method="POST")
req.add_header("Content-Type", "application/json")

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode()
        data = json.loads(body)
        print("STATUS: 200 OK")
        print(f"Results count: {len(data.get('results', []))}")
        for r in data.get("results", []):
            print(f"  strategy={r['strategy']} cases={r['cases_processed']} net={r['net_recovery_paise']}")
except Exception as e:
    print(f"ERROR: {e}")
