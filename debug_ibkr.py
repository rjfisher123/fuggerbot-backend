
import logging
import os
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from ib_insync import IB

def test_connection():
    print("Testing IBKR Connection...")
    host = "127.0.0.1"
    port = 7497 
    client_id = 123 # Random ID
    
    ib = IB()
    try:
        print(f"Connecting to {host}:{port} with clientId={client_id}...")
        ib.connect(host=host, port=port, clientId=client_id, timeout=10)
        print("✅ SUCCESS: Connected to IBKR!")
        print(f"Account: {ib.accountValues()[:1]}")
        ib.disconnect()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_connection()
