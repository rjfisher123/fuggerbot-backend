# IBKR Auto-Connect Setup

## ✅ Auto-Connect is Now Enabled by Default!

FuggerBot will now automatically connect to IBKR (TWS/IB Gateway) when the trader is initialized.

## How It Works

1. **Automatic Connection**: When `get_ibkr_trader()` is called, it will automatically attempt to connect
2. **Retry Logic**: If connection fails, it will retry up to 3 times with exponential backoff
3. **Graceful Failure**: If TWS/IB Gateway isn't running, it will log a warning but continue

## Configuration

### Enable/Disable Auto-Connect

You can control auto-connect behavior in two ways:

#### Option 1: Environment Variable (Recommended)
Add to your `.env` file:
```bash
# Enable auto-connect (default: true)
IBKR_AUTO_CONNECT=true

# Or disable it
IBKR_AUTO_CONNECT=false
```

#### Option 2: Code Parameter
```python
from core.ibkr_trader import get_ibkr_trader

# Auto-connect enabled (default)
trader = get_ibkr_trader(auto_connect=True)

# Auto-connect disabled
trader = get_ibkr_trader(auto_connect=False)
```

## Connection Behavior

### On Startup:
- ✅ Automatically attempts to connect to IBKR
- ✅ Retries up to 3 times if connection fails
- ✅ Logs connection status clearly

### If TWS/IB Gateway is Running:
- ✅ Connects automatically
- ✅ Shows success message: `✅ Connected to IBKR at 127.0.0.1:7497`

### If TWS/IB Gateway is NOT Running:
- ⚠️ Logs warning but doesn't crash
- ℹ️ You can manually connect later
- 🔄 Will retry when `get_ibkr_trader()` is called again

## Manual Connection

If auto-connect fails, you can still connect manually:

```python
from core.ibkr_trader import get_ibkr_trader

trader = get_ibkr_trader(auto_connect=False)
trader.connect()  # Manual connection
```

## Troubleshooting

### Connection Fails?
1. **Check TWS/IB Gateway is running**
   ```bash
   # Check if port is listening
   lsof -i :7497  # Paper trading
   lsof -i :7496  # Live trading
   ```

2. **Verify API is enabled**
   - Open TWS/IB Gateway
   - File > Global Configuration > API > Settings
   - Check "Enable ActiveX and Socket Clients"
   - Verify port matches your config

3. **Check environment variables**
   ```bash
   # In your .env file
   IBKR_HOST=127.0.0.1
   IBKR_PORT=7497  # 7497 for paper, 7496 for live
   IBKR_CLIENT_ID=1
   IBKR_AUTO_CONNECT=true
   ```

## Benefits

- ✅ **No manual connection needed** - Just start TWS/IB Gateway and FuggerBot connects automatically
- ✅ **Resilient** - Retries on failure, doesn't crash if connection unavailable
- ✅ **Configurable** - Can disable if needed via env var or parameter
- ✅ **Smart** - Only connects when needed, reuses existing connections

## Status

Auto-connect is **enabled by default**. Just make sure TWS/IB Gateway is running before using FuggerBot!










