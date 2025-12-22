# IBKR Paper Trading vs Live Trading Separation

## Overview

FuggerBot now properly separates IBKR's **Paper Trading API** (port 7497) from the **Live Trading API** (port 7496), routing them to the appropriate views in the dashboard.

## Architecture

### Paper Trading API → Paper Trading Panel
- **Port**: 7497 (IBKR paper trading)
- **View**: 📊 Paper Trading tab
- **Purpose**: Test strategies with IBKR's paper trading account (no real money)
- **Function**: `get_paper_trading_trader()`

### Live Trading API → Trade Approval Panel
- **Port**: 7496 (IBKR live trading)
- **View**: 💰 Trade Approval tab
- **Purpose**: Execute real trades with approval workflow
- **Function**: `get_live_trading_trader()`

## Implementation Details

### Core Changes

1. **`IBKRTrader` class**:
   - Added `is_paper_trading` property (determined by port: 7497 = paper, 7496 = live)

2. **`get_ibkr_trader()` function**:
   - Added `paper_trading` parameter
   - Automatically selects port based on mode:
     - `paper_trading=True` → port 7497
     - `paper_trading=False` → port 7496
     - `paper_trading=None` → uses `IBKR_PORT` env var (defaults to 7497)

3. **Helper functions**:
   - `get_paper_trading_trader()`: Returns trader connected to paper trading API
   - `get_live_trading_trader()`: Returns trader connected to live trading API

### Dashboard Integration

#### Paper Trading Panel (`dash/components/paper_trading_panel.py`)
- **IBKR Paper Trading Integration** section:
  - Connects to IBKR paper trading API (port 7497)
  - Executes trades in paper account (no approval needed)
  - Also tracks trades in virtual simulation engine
- **Virtual Simulation** section:
  - Pure simulation (no IBKR connection required)
  - For testing strategies without any broker

#### Trade Approval Panel (`dash/components/trade_approval.py`)
- Uses `get_live_trading_trader()` for all operations
- Connects to IBKR live trading API (port 7496)
- Requires SMS approval for all trades
- Shows connection status with mode indicator

## Environment Variables

You can configure ports via environment variables:

```bash
# Paper Trading (default)
IBKR_PAPER_PORT=7497

# Live Trading
IBKR_LIVE_PORT=7496

# Default (used if paper_trading is None)
IBKR_PORT=7497
```

## Usage Examples

### In Code

```python
from core.ibkr_trader import get_paper_trading_trader, get_live_trading_trader

# Paper trading
paper_trader = get_paper_trading_trader()
if paper_trader.connected:
    result = paper_trader.execute_trade(
        symbol="AAPL",
        action="BUY",
        quantity=10,
        order_type="MARKET",
        require_confirmation=False  # Paper trading - no approval needed
    )

# Live trading
live_trader = get_live_trading_trader()
if live_trader.connected:
    result = live_trader.execute_trade(
        symbol="AAPL",
        action="BUY",
        quantity=10,
        order_type="MARKET",
        require_confirmation=True  # Live trading - requires SMS approval
    )
```

### In Dashboard

1. **Paper Trading Tab**:
   - Shows IBKR Paper Trading connection status
   - Execute trades directly in paper account
   - Also has virtual simulation (no broker needed)

2. **Trade Approval Tab**:
   - Shows IBKR Live Trading connection status
   - All trades require SMS approval
   - Displays pending approvals and trade history

## Benefits

1. **Clear Separation**: No confusion between paper and live trading
2. **Safety**: Live trading always requires approval
3. **Flexibility**: Can test with IBKR paper account or pure simulation
4. **Transparency**: Connection status clearly shows which mode is active

## Port Reference

- **7497**: IBKR Paper Trading (default)
- **7496**: IBKR Live Trading
- **4002**: Custom port (if you've configured IB Gateway differently)

## Notes

- Both APIs can run simultaneously (different ports)
- Paper trading trades don't require SMS approval
- Live trading trades always require SMS approval
- The virtual simulation in Paper Trading panel doesn't require any IBKR connection










