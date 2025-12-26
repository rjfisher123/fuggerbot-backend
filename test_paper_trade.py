#!/usr/bin/env python
"""Test paper trade execution via the API."""

from execution.ibkr import IBKRBridge
from ib_insync import MarketOrder

print("🧪 Testing Paper Trade Execution\n")

# Create a new bridge with unique client ID
print("1. Creating IBKR bridge (client_id=200)...")
bridge = IBKRBridge(host="127.0.0.1", port=7497, client_id=200)

# Connect
print("2. Connecting to IB Gateway...")
success = bridge.connect()
if not success:
    print("❌ Failed to connect!")
    exit(1)

# Get contract
print("3. Getting BTC-USD contract...")
contract = bridge.get_contract('BTC-USD')
print(f"   Contract: {contract}")

# Create market order for 0.001 BTC
print("4. Placing MARKET order for 0.001 BTC...")
order = MarketOrder('BUY', 0.001)
trade = bridge.ib.placeOrder(contract, order)

print(f"\n✅ Trade placed!")
print(f"   Order ID: {trade.order.orderId}")
print(f"   Status: {trade.orderStatus.status}")
print(f"   Trade: {trade}")

