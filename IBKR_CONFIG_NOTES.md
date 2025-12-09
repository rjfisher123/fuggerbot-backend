# IBKR Gateway Configuration Notes

Based on your current IB Gateway settings:

## Current Settings Detected:
- **Socket Port**: 4002 (not the default 7497)
- **Read-Only API**: ✅ Checked (needs to be unchecked for trading)
- **Allow connections from localhost only**: ✅ Checked (good for security)
- **Trusted IPs**: 127.0.0.1

## Required Changes for Trading:

### 1. Update Socket Port in .env
Your IB Gateway is using port **4002**, so update your `.env` file:

```bash
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
```

### 2. Uncheck "Read-Only API"
To execute trades (not just view data), you need to:
- Go to: API > Settings
- **Uncheck** "Read-Only API"
- Click "OK" or "Apply"
- Restart IB Gateway

### 3. Optional: Enable Order Precautions Bypass
If you want automated trading without manual confirmation in TWS:
- Go to: API > Precautions
- Check "Bypass Order Precautions for API Orders"

## Testing Connection:

After updating your `.env` file with port 4002:

```bash
python test_ibkr.py
```

Or test from the dashboard - the connection should work now!

## Port Reference:
- **4002**: Your current IB Gateway port (simulated trading)
- **7497**: Default paper trading port (if you change it)
- **7496**: Default live trading port


