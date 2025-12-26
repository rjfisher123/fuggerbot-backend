"""
Simple IBKR Connection Test.

Attempts a basic connection to verify TWS/Gateway is accepting API connections.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ib_insync import IB
import time

def test_connection(port=7497, timeout=10):
    """Test connection with detailed logging."""
    print(f"\n{'='*80}")
    print(f"Testing IBKR Connection on Port {port}")
    print(f"{'='*80}\n")
    
    ib = IB()
    
    try:
        print(f"Step 1: Creating IB instance... ✅")
        print(f"Step 2: Attempting connection to 127.0.0.1:{port}...")
        print(f"         (Timeout: {timeout} seconds)")
        print(f"         Client ID: 1")
        
        # Try to connect
        ib.connect('127.0.0.1', port, clientId=1, timeout=timeout)
        
        print(f"\nStep 3: Checking connection status...")
        if ib.isConnected():
            print(f"✅ CONNECTION SUCCESSFUL!")
            
            # Get account info
            print(f"\nStep 4: Retrieving account information...")
            accounts = ib.managedAccounts()
            print(f"   Managed Accounts: {accounts}")
            
            # Get connection time
            current_time = ib.reqCurrentTime()
            print(f"   Server Time: {current_time}")
            
            # Disconnect
            print(f"\nStep 5: Disconnecting...")
            ib.disconnect()
            print(f"✅ Disconnected successfully")
            
            return True
        else:
            print(f"❌ Connection failed (isConnected returned False)")
            return False
            
    except TimeoutError as e:
        print(f"\n❌ CONNECTION TIMEOUT")
        print(f"   Error: {e}")
        print(f"\n💡 POSSIBLE CAUSES:")
        print(f"   1. TWS API is not enabled")
        print(f"   2. Socket port is incorrect")
        print(f"   3. Client ID conflict")
        print(f"   4. TWS is still loading")
        print(f"\n💡 TO FIX:")
        print(f"   1. Open TWS")
        print(f"   2. Go to: File → Global Configuration → API → Settings")
        print(f"   3. Check 'Enable ActiveX and Socket Clients'")
        print(f"   4. Verify Socket port is {port}")
        print(f"   5. Add 127.0.0.1 to 'Trusted IP addresses'")
        print(f"   6. Click OK and wait 10 seconds")
        print(f"   7. Re-run this test")
        return False
        
    except ConnectionRefusedError as e:
        print(f"\n❌ CONNECTION REFUSED")
        print(f"   Error: {e}")
        print(f"\n💡 POSSIBLE CAUSES:")
        print(f"   1. TWS/Gateway is not running")
        print(f"   2. Wrong port number")
        print(f"\n💡 TO FIX:")
        print(f"   1. Make sure TWS or IB Gateway is running")
        print(f"   2. Check the port number (7497 for paper, 7496 for live)")
        return False
        
    except Exception as e:
        print(f"\n❌ CONNECTION ERROR")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {e}")
        return False
    
    finally:
        if ib.isConnected():
            try:
                ib.disconnect()
            except:
                pass


def main():
    """Run connection tests."""
    print("\n" + "="*80)
    print("IBKR SIMPLE CONNECTION TEST")
    print("="*80)
    
    # Test common ports
    ports_to_test = [
        (7497, "Paper Trading (TWS)"),
        (7496, "Live Trading (TWS)"),
        (4001, "Paper Trading (Gateway)"),
        (4002, "Live Trading (Gateway)")
    ]
    
    successful_ports = []
    
    for port, description in ports_to_test:
        print(f"\n\n{'='*80}")
        print(f"Testing {description} - Port {port}")
        print(f"{'='*80}")
        
        # Quick port check first
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result != 0:
            print(f"❌ Port {port} is not listening - skipping")
            continue
        
        print(f"✅ Port {port} is listening - attempting connection...")
        
        if test_connection(port, timeout=5):
            successful_ports.append(port)
    
    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if successful_ports:
        print(f"\n✅ SUCCESS! Working ports: {successful_ports}")
        print(f"\n💡 To use in FuggerBot:")
        print(f"   export IBKR_PORT={successful_ports[0]}")
        print(f"   # Or add to .env file:")
        print(f"   echo 'IBKR_PORT={successful_ports[0]}' >> .env")
        return True
    else:
        print(f"\n❌ FAILED - No working IBKR connections found")
        print(f"\n💡 TROUBLESHOOTING STEPS:")
        print(f"   1. Verify TWS/Gateway is running and fully loaded")
        print(f"   2. Check TWS API Settings:")
        print(f"      File → Global Configuration → API → Settings")
        print(f"      - Enable 'Enable ActiveX and Socket Clients'")
        print(f"      - Socket port: 7497 (paper) or 7496 (live)")
        print(f"      - Trusted IPs: Add 127.0.0.1")
        print(f"   3. Restart TWS/Gateway after changing settings")
        print(f"   4. Wait 10-15 seconds for TWS to fully initialize")
        print(f"   5. Re-run this test")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

