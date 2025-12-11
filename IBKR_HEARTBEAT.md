# IBKR Heartbeat Worker

The IBKR heartbeat worker continuously monitors IBKR connection status, attempts automatic reconnection on failure, and updates the database with real-time status information.

## Features

- **Continuous Monitoring**: Polls connection status every 30 seconds (configurable)
- **Automatic Reconnection**: Attempts to reconnect when connection is lost
- **Database Tracking**: Stores connection status, timestamps, and reconnect attempts
- **Real-Time UI Updates**: `/trades` page auto-refreshes connection status every 5 seconds using HTMX

## Usage

### Run Once (Testing)
```bash
python3 -m workers.ibkr_heartbeat --once
```

### Run Continuously
```bash
# Default 30 second interval
python3 -m workers.ibkr_heartbeat

# Custom interval (e.g., 15 seconds)
python3 -m workers.ibkr_heartbeat --interval 15

# Disable automatic reconnection
python3 -m workers.ibkr_heartbeat --no-auto-reconnect
```

### Run as Background Service

For production, you can run the worker as a background service:

```bash
# Using nohup
nohup python3 -m workers.ibkr_heartbeat --interval 30 > ibkr_heartbeat.log 2>&1 &

# Or using screen/tmux
screen -S ibkr_heartbeat
python3 -m workers.ibkr_heartbeat --interval 30
# Press Ctrl+A then D to detach
```

## Database Schema

The worker updates the `ibkr_status` table with:

- `paper_trading`: Boolean indicating paper vs live trading
- `connected`: Current connection status
- `host`, `port`, `client_id`: Connection details
- `last_checked`: Timestamp of last status check
- `last_connected`: Timestamp of last successful connection
- `reconnect_attempts`: Number of reconnection attempts since last connection
- `error_message`: Error details if connection failed

## UI Integration

The `/trades` page automatically polls the connection status every 5 seconds using HTMX. The status is displayed with:

- ✅ Green alert when connected
- ⚠️ Yellow alert when disconnected
- Last checked timestamp
- Reconnect attempt count (if disconnected)

## How It Works

1. **Heartbeat Check**: Every N seconds, the worker checks connection status for both paper and live trading accounts
2. **Status Update**: Current status is written to the database
3. **Auto-Reconnect**: If disconnected and `auto_reconnect=True`, attempts to reconnect
4. **UI Polling**: The `/trades` page polls `/trades/status` endpoint every 5 seconds to get the latest status from the database

## Monitoring

Check the worker logs to see:
- Connection status changes
- Reconnection attempts
- Errors and warnings

Example log output:
```
IBKR Heartbeat: Paper ✅ | Live ❌
✅ Reconnected to IBKR Live
❌ Failed to reconnect to IBKR Paper
```





