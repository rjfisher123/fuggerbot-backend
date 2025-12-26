#!/usr/bin/env python
"""Quick test of the trade API endpoint."""

import requests
import json

print("Testing Trade API...")

# 1. Check connection
print("\n1. Checking IBKR connection...")
resp = requests.get("http://localhost:8000/api/ibkr/status")
print(f"   Status: {resp.status_code}")
print(f"   {json.dumps(resp.json(), indent=2)}")

if not resp.json().get("connected"):
    print("\n   Connecting...")
    resp = requests.post(
        "http://localhost:8000/api/ibkr/connect",
        json={"port": 7497},
        timeout=15
    )
    print(f"   Connect result: {resp.json()}")

# 2. Place trade
print("\n2. Placing trade for 1 share of NVDA...")
try:
    resp = requests.post(
        "http://localhost:8000/api/trade/execute",
        json={
            "symbol": "NVDA",
            "action": "BUY",
            "quantity": 1,
            "order_type": "MARKET"
        },
        timeout=15
    )
    print(f"   Response status: {resp.status_code}")
    print(f"   Response: {json.dumps(resp.json(), indent=2)}")
except requests.Timeout:
    print("   ❌ Request timed out after 15 seconds")
except Exception as e:
    print(f"   ❌ Error: {e}")

