# IBKR (Interactive Brokers) Integration Setup

This guide will help you set up automated trading with Interactive Brokers through FuggerBot.

## Prerequisites

1. **IBKR Account**: Active Interactive Brokers account (paper trading or live)
2. **TWS or IB Gateway**: Download from [IBKR website](https://www.interactivebrokers.com/en/trading/tws.php)
3. **Python Package**: `ib_insync` (included in requirements.txt)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `ib_insync`, which is a user-friendly Python wrapper for the IBKR API.

## Step 2: Configure TWS/IB Gateway for API Access

1. **Open TWS or IB Gateway**
2. **Enable API Access**:
   - Go to `File` > `Global Configuration` > `API` > `Settings`
   - Check "Enable ActiveX and Socket Clients"
   - **Uncheck** "Read-Only API" (if you want to place orders)
   - Set Socket Port:
     - **7497** for paper trading
     - **7496** for live trading
   - Check "Allow connections from localhost only" (recommended for security)

3. **Configure Order Precautions** (Optional but Recommended):
   - Go to `API` > `Precautions`
   - Enable "Bypass Order Precautions for API Orders" (if you want automated trading)

4. **Save and Restart** TWS/IB Gateway

## Step 3: Configure Environment Variables

Add IBKR settings to your `.env` file:

```bash
# IBKR Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=7497          # 7497 for paper, 7496 for live
IBKR_CLIENT_ID=1
```

## Step 4: Start TWS/IB Gateway

**Important**: TWS or IB Gateway must be running for FuggerBot to connect.

- For paper trading: Use IB Gateway (lighter weight)
- For live trading: Use TWS or IB Gateway

## Step 5: Configure Triggers with Trade Actions

In the Streamlit dashboard or `dash/data/triggers.json`, configure triggers with trading actions:

```json
{
  "symbol": "INTC",
  "condition": "<",
  "price": 22.0,
  "action": "buy",
  "quantity": 10,
  "order_type": "MARKET"
}
```

**Action Types:**
- `notify`: Send SMS alert only (no trade)
- `buy`: Request approval to buy shares
- `sell`: Request approval to sell shares
- `layer_in`: Buy incrementally (buy action with confirmation)

**Order Types:**
- `MARKET`: Execute at current market price
- `LIMIT`: Execute at specified limit price (requires `limit_price` field)

## Step 6: How Trade Confirmation Works

1. **Trigger Fires**: When a price trigger is hit, FuggerBot:
   - Sends an SMS alert with the trigger details
   - If action is `buy`, `sell`, or `layer_in`, sends a second SMS with:
     - Trade details (symbol, action, quantity, price)
     - **6-digit approval code**

2. **Approve Trade**: 
   - Go to the FuggerBot dashboard
   - Navigate to the "Trade Approval" section
   - Enter the 6-digit approval code from SMS
   - Click "Approve & Execute"
   - Trade is executed via IBKR API

3. **Approval Expiration**: Approval codes expire after 15 minutes

## Example Workflow

1. Set trigger: "Buy 10 shares of INTC if price drops below $22"
2. INTC price drops to $21.50
3. You receive SMS: "🚨 INTC dropped below $22.00 (current: $21.50)"
4. You receive second SMS: "🚨 FUGGERBOT TRADE REQUEST... Approval Code: 123456"
5. Open dashboard, enter code 123456, click "Approve & Execute"
6. Trade executes: 10 shares of INTC purchased at market price

## Testing

### Test Connection
```python
from core.ibkr_trader import get_ibkr_trader

trader = get_ibkr_trader()
if trader.connect():
    print("✅ Connected to IBKR!")
    trader.disconnect()
```

### Test Trade (Paper Trading)
1. Make sure TWS/IB Gateway is running
2. Create a trigger with `action: "buy"` and `quantity: 1`
3. Wait for trigger to fire
4. Check SMS for approval code
5. Approve via dashboard

## Security Notes

- **Always use paper trading first** to test your setup
- Approval codes expire after 15 minutes
- TWS/IB Gateway must be running for trades to execute
- Consider using "Allow connections from localhost only" in TWS settings
- Keep your `.env` file secure (never commit it to git)

## Troubleshooting

### "Not connected to IBKR"
- Make sure TWS/IB Gateway is running
- Check that API is enabled in TWS settings
- Verify port number matches your `.env` file
- Try connecting manually: `trader.connect()`

### "Could not get contract for SYMBOL"
- Verify symbol is correct (use IBKR symbol format)
- Check that TWS/IB Gateway is connected to market data
- Some symbols may require specific exchange specification

### "Order failed"
- Check account permissions (some accounts may have trading restrictions)
- Verify you have sufficient buying power or shares to sell
- Check TWS for any error messages

## Resources

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [ib_insync Documentation](https://ib-insync.readthedocs.io/)
- [IBKR Quant News](https://www.interactivebrokers.com/campus/ibkr-quant-news/)


