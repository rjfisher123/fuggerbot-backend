"""
IBKR Connection Diagnostic Tool.

Helps diagnose why IBKR isn't connecting by checking:
1. TWS/Gateway process status
2. Port availability
3. Network connectivity
4. Configuration
"""
import sys
from pathlib import Path
import socket
import subprocess
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_tws_process():
    """Check if TWS or IB Gateway is running."""
    print("\n" + "=" * 80)
    print("CHECKING: TWS/IB Gateway Process")
    print("=" * 80)
    
    try:
        # Check for TWS/Gateway processes
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        
        tws_processes = []
        for line in result.stdout.split('\n'):
            if any(keyword in line.lower() for keyword in ['tws', 'ibgateway', 'interactive brokers']):
                if 'grep' not in line:
                    tws_processes.append(line)
        
        if tws_processes:
            print("✅ Found TWS/Gateway processes:")
            for proc in tws_processes:
                print(f"   {proc[:120]}...")
            return True
        else:
            print("❌ No TWS/Gateway processes found")
            print("\n💡 SOLUTION:")
            print("   1. Open Interactive Brokers TWS or IB Gateway")
            print("   2. Log in with your credentials")
            print("   3. For Paper Trading: Use port 7497")
            print("   4. For Live Trading: Use port 7496")
            return False
            
    except Exception as e:
        print(f"⚠️  Error checking processes: {e}")
        return False


def check_port_availability():
    """Check if IBKR ports are listening."""
    print("\n" + "=" * 80)
    print("CHECKING: Port Availability")
    print("=" * 80)
    
    ports_to_check = {
        7497: "Paper Trading (TWS)",
        7496: "Live Trading (TWS)",
        4001: "Paper Trading (Gateway)",
        4002: "Live Trading (Gateway)"
    }
    
    available_ports = []
    
    for port, description in ports_to_check.items():
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                print(f"✅ Port {port} ({description}): LISTENING")
                available_ports.append(port)
            else:
                print(f"❌ Port {port} ({description}): NOT LISTENING")
                
        except Exception as e:
            print(f"⚠️  Error checking port {port}: {e}")
    
    if available_ports:
        print(f"\n✅ Found {len(available_ports)} available port(s): {available_ports}")
        return available_ports
    else:
        print("\n❌ No IBKR ports are listening")
        print("\n💡 SOLUTION:")
        print("   1. Make sure TWS/Gateway is running")
        print("   2. Check TWS Configuration:")
        print("      - File → Global Configuration → API → Settings")
        print("      - Enable 'Enable ActiveX and Socket Clients'")
        print("      - Socket port should be 7497 (paper) or 7496 (live)")
        print("      - Trusted IP addresses should include 127.0.0.1")
        return []


def check_network_connectivity():
    """Test basic network connectivity to localhost."""
    print("\n" + "=" * 80)
    print("CHECKING: Network Connectivity")
    print("=" * 80)
    
    try:
        # Try to connect to localhost
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 80))
        sock.close()
        
        print("✅ Localhost network stack is functional")
        return True
        
    except Exception as e:
        print(f"❌ Network connectivity issue: {e}")
        return False


def check_configuration():
    """Check FuggerBot IBKR configuration."""
    print("\n" + "=" * 80)
    print("CHECKING: FuggerBot Configuration")
    print("=" * 80)
    
    # Check environment variables
    ibkr_host = os.getenv("IBKR_HOST", "127.0.0.1")
    ibkr_port = os.getenv("IBKR_PORT", "7497")
    
    print(f"Environment Variables:")
    print(f"   IBKR_HOST: {ibkr_host}")
    print(f"   IBKR_PORT: {ibkr_port}")
    
    # Check .env file
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print(f"\n✅ .env file found at {env_file}")
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                if 'IBKR_HOST' in content or 'IBKR_PORT' in content:
                    print("   Contains IBKR configuration")
                else:
                    print("   ⚠️  No IBKR configuration in .env file")
        except Exception as e:
            print(f"   ⚠️  Error reading .env: {e}")
    else:
        print(f"\n⚠️  No .env file found at {env_file}")
        print("   Using default values (host=127.0.0.1, port=7497)")
    
    return True


def test_connection():
    """Attempt a test connection to IBKR."""
    print("\n" + "=" * 80)
    print("TESTING: Direct Connection Attempt")
    print("=" * 80)
    
    ports_to_try = [7497, 7496, 4001, 4002]
    
    for port in ports_to_try:
        print(f"\nTrying port {port}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"✅ Port {port} is REACHABLE")
                
                # Try actual IBKR connection
                try:
                    from ib_insync import IB
                    ib = IB()
                    print(f"   Attempting IBKR connection...")
                    ib.connect('127.0.0.1', port, clientId=999, timeout=3)
                    
                    if ib.isConnected():
                        print(f"   ✅ IBKR CONNECTION SUCCESSFUL on port {port}!")
                        accounts = ib.managedAccounts()
                        print(f"   Accounts: {accounts}")
                        ib.disconnect()
                        return port
                    else:
                        print(f"   ❌ Socket connected but IBKR handshake failed")
                        
                except Exception as e:
                    print(f"   ❌ IBKR connection failed: {e}")
            else:
                print(f"❌ Port {port} is NOT REACHABLE")
                
        except Exception as e:
            print(f"❌ Error testing port {port}: {e}")
    
    return None


def provide_recommendations(results):
    """Provide actionable recommendations based on diagnostic results."""
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    if results['working_port']:
        print(f"\n✅ IBKR is working on port {results['working_port']}!")
        print(f"\n💡 To use this port in FuggerBot:")
        print(f"   1. Set environment variable: export IBKR_PORT={results['working_port']}")
        print(f"   2. Or add to .env file: IBKR_PORT={results['working_port']}")
        print(f"   3. Restart your application")
        
    elif not results['tws_running']:
        print("\n❌ TWS/Gateway is NOT running")
        print("\n💡 STEPS TO FIX:")
        print("   1. Launch Interactive Brokers TWS or IB Gateway")
        print("   2. Log in with your credentials")
        print("   3. Wait for the application to fully load")
        print("   4. Re-run this diagnostic")
        
    elif not results['ports_available']:
        print("\n❌ TWS/Gateway is running but API is NOT enabled")
        print("\n💡 STEPS TO FIX:")
        print("   1. In TWS: File → Global Configuration → API → Settings")
        print("   2. Check 'Enable ActiveX and Socket Clients'")
        print("   3. Set Socket port:")
        print("      - Paper Trading: 7497")
        print("      - Live Trading: 7496")
        print("   4. Add 127.0.0.1 to Trusted IP addresses")
        print("   5. Click OK and restart TWS")
        
    else:
        print("\n⚠️  TWS is running and ports are listening, but connection failed")
        print("\n💡 POSSIBLE ISSUES:")
        print("   1. Client ID conflict (another app using same ID)")
        print("   2. IP address not trusted in TWS settings")
        print("   3. API permissions not enabled for your account")
        print("   4. Firewall blocking connection")
        print("\n💡 TRY:")
        print("   - Restart TWS/Gateway")
        print("   - Check TWS API settings (File → Global Configuration → API)")
        print("   - Try a different client ID")


def run_diagnostics():
    """Run all diagnostic checks."""
    print("\n" + "=" * 80)
    print("IBKR CONNECTION DIAGNOSTICS")
    print("=" * 80)
    
    results = {
        'tws_running': False,
        'ports_available': [],
        'network_ok': False,
        'config_ok': False,
        'working_port': None
    }
    
    # Run checks
    results['tws_running'] = check_tws_process()
    results['ports_available'] = check_port_availability()
    results['network_ok'] = check_network_connectivity()
    results['config_ok'] = check_configuration()
    results['working_port'] = test_connection()
    
    # Provide recommendations
    provide_recommendations(results)
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"TWS/Gateway Running: {'✅' if results['tws_running'] else '❌'}")
    print(f"Ports Available: {'✅' if results['ports_available'] else '❌'} {results['ports_available']}")
    print(f"Network OK: {'✅' if results['network_ok'] else '❌'}")
    print(f"Configuration OK: {'✅' if results['config_ok'] else '❌'}")
    print(f"Working Port: {'✅ ' + str(results['working_port']) if results['working_port'] else '❌ None'}")
    
    if results['working_port']:
        print("\n🎉 IBKR connection is working!")
        return True
    else:
        print("\n❌ IBKR connection is NOT working")
        print("   Review recommendations above to fix the issue")
        return False


if __name__ == "__main__":
    success = run_diagnostics()
    sys.exit(0 if success else 1)

