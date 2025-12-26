from ib_insync import IB

ports = [7497, 7496, 4001, 4002]

for port in ports:
    print(f"\nTrying port {port}...")
    ib = IB()
    try:
        ib.connect('127.0.0.1', port, clientId=1, timeout=3)
        if ib.isConnected():
            print(f"✅ SUCCESS on port {port}!")
            print(f"   Accounts: {ib.managedAccounts()}")
            ib.disconnect()
            break
        else:
            print(f"❌ Failed on port {port}")
    except Exception as e:
        print(f"❌ Error on port {port}: {str(e)[:50]}")
        
print("\nDone!")
