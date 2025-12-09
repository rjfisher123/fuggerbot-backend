#!/usr/bin/env python3
"""Test script for IBKR sandbox/paper trading connection."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from core.ibkr_trader import get_ibkr_trader
from core.logger import logger

def test_ibkr_connection():
    """Test connection to IBKR sandbox."""
    print("=" * 60)
    print("Testing IBKR Sandbox Connection")
    print("=" * 60)
    
    # Get configuration
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "7497"))  # Default: 7497 (paper), 7496 (live), or your custom port
    client_id = int(os.getenv("IBKR_CLIENT_ID", "1"))
    
    print(f"\nConfiguration:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"    (Common ports: 7497=paper, 7496=live, 4002=your current IB Gateway)")
    print(f"  Client ID: {client_id}")
    print(f"\n⚠️  Make sure TWS or IB Gateway is running!")
    print(f"⚠️  Make sure 'Read-Only API' is UNCHECKED if you want to trade!")
    print()
    
    try:
        # Get trader instance
        trader = get_ibkr_trader(host, port, client_id)
        
        # Test connection
        print("Attempting to connect...")
        if trader.connect():
            print("✅ Successfully connected to IBKR!")
            
            # Test getting account info
            print("\nTesting API calls...")
            try:
                # Get account values
                account_values = trader.ib.accountValues()
                if account_values:
                    print(f"✅ Retrieved {len(account_values)} account values")
                    # Show a few key values
                    key_tags = ['NetLiquidation', 'TotalCashValue', 'BuyingPower', 'GrossPositionValue']
                    shown = False
                    for av in account_values:
                        if av.tag in key_tags:
                            print(f"   {av.tag}: {av.value} ({av.currency})")
                            shown = True
                    if not shown and account_values:
                        # Show first 5 if no key tags found
                        for av in account_values[:5]:
                            print(f"   {av.tag}: {av.value} ({av.currency})")
                else:
                    print("⚠️  No account values returned")
            except Exception as e:
                print(f"⚠️  Could not get account values: {e}")
            
            # Test getting a contract
            print("\nTesting contract lookup...")
            test_symbol = "AAPL"
            print(f"Looking up contract for {test_symbol}...")
            contract = trader.get_contract(test_symbol)
            
            if contract:
                print(f"✅ Successfully retrieved contract:")
                print(f"   Symbol: {contract.symbol}")
                print(f"   Exchange: {contract.exchange}")
                print(f"   Currency: {contract.currency}")
                print(f"   SecType: {contract.secType}")
            else:
                print(f"⚠️  Could not retrieve contract for {test_symbol}")
            
            # Test getting market price
            print(f"\nTesting market price for {test_symbol}...")
            price = trader.get_market_price(test_symbol)
            if price:
                print(f"✅ Current market price: ${price:.2f}")
            else:
                print(f"⚠️  Could not get market price")
            
            # Disconnect
            trader.disconnect()
            print("\n✅ Disconnected from IBKR")
            
        else:
            print("❌ Failed to connect to IBKR")
            print("\nTroubleshooting:")
            print("1. Make sure TWS or IB Gateway is running")
            print("2. Check that API is enabled in TWS settings:")
            print("   File > Global Configuration > API > Settings")
            print("   - Enable 'Enable ActiveX and Socket Clients'")
            print("   - Set Socket Port to 7497 (paper) or 7496 (live)")
            print("3. Verify the port number matches your .env file")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure ib_insync is installed:")
        print("  pip install ib_insync")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Test error: {e}", exc_info=True)
        return False
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_ibkr_connection()
    sys.exit(0 if success else 1)

