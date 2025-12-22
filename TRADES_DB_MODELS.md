# Trade Database Models and Repositories

Database models and repositories for managing trade requests and executions.

## Models

### TradeRequest (`persistence/models_trades.py`)

Represents a pending trade approval request.

**Fields:**
- `id`: Primary key
- `trade_id`: Unique trade identifier (indexed)
- `approval_code`: Approval code for this request (indexed)
- `symbol`: Trading symbol (indexed)
- `action`: BUY or SELL
- `quantity`: Number of shares
- `order_type`: MARKET, LIMIT, etc.
- `price`: Limit price if applicable
- `status`: pending, approved, rejected, expired (indexed)
- `requested_at`: When request was created (indexed)
- `expires_at`: When request expires (indexed)
- `approved_at`: When request was approved
- `rejected_at`: When request was rejected
- `forecast_id`: Optional link to forecast (indexed)
- `trade_details`: JSON string for additional details
- `paper_trading`: Whether this is paper trading (indexed)

**Relationships:**
- `executions`: One-to-many relationship with TradeExecution

### TradeExecution (`persistence/models_trades.py`)

Represents an executed trade (fill, IBKR response).

**Fields:**
- `id`: Primary key
- `trade_request_id`: Foreign key to TradeRequest (indexed)
- `symbol`: Trading symbol (indexed)
- `action`: BUY or SELL
- `quantity`: Number of shares executed
- `execution_price`: Price at which trade was executed
- `execution_time`: When trade was executed (indexed)
- `order_id`: Broker order ID (indexed)
- `status`: Filled, PartiallyFilled, Submitted, Rejected, etc.
- `broker_response`: JSON string for full broker response
- `forecast_id`: Optional link to forecast (indexed)
- `paper_trading`: Whether this is paper trading (indexed)
- `error_message`: Optional error message

**Relationships:**
- `trade_request`: Many-to-one relationship with TradeRequest

## Repositories

### TradeRequestRepository (`persistence/repositories_trades.py`)

**Methods:**

1. **`add_trade_request(...)`**
   - Creates a new trade request
   - Returns: TradeRequest

2. **`list_pending_requests(paper_trading=None, include_expired=False)`**
   - Lists all pending trade requests
   - Can filter by paper_trading
   - Can include/exclude expired requests
   - Returns: List[TradeRequest]

3. **`update_request_status(trade_id, status, approval_code=None)`**
   - Updates trade request status (approved, rejected, expired)
   - Automatically sets approved_at or rejected_at timestamps
   - Can find by trade_id or approval_code
   - Returns: TradeRequest or None

4. **`get_by_trade_id(trade_id)`**
   - Gets trade request by trade_id
   - Returns: TradeRequest or None

5. **`get_by_approval_code(approval_code)`**
   - Gets trade request by approval_code
   - Returns: TradeRequest or None

6. **`list_all(paper_trading=None, limit=100)`**
   - Lists all trade requests (not just pending)
   - Returns: List[TradeRequest]

### TradeExecutionRepository (`persistence/repositories_trades.py`)

**Methods:**

1. **`record_execution(...)`**
   - Records a trade execution
   - Links to TradeRequest via trade_request_id
   - Stores broker response as JSON
   - Returns: TradeExecution

2. **`get_by_trade_request_id(trade_request_id)`**
   - Gets all executions for a trade request
   - Returns: List[TradeExecution]

3. **`list_recent(paper_trading=None, limit=100)`**
   - Lists recent trade executions
   - Returns: List[TradeExecution]

## Usage Example

```python
from persistence.db import SessionLocal
from persistence.repositories_trades import TradeRequestRepository, TradeExecutionRepository
from datetime import datetime, timedelta

with SessionLocal() as session:
    # Create repository
    request_repo = TradeRequestRepository(session)
    
    # Add a trade request
    trade_request = request_repo.add_trade_request(
        trade_id="TRADE001",
        approval_code="123456",
        symbol="AAPL",
        action="BUY",
        quantity=10,
        order_type="MARKET",
        expires_at=datetime.utcnow() + timedelta(minutes=30),
        forecast_id="FCST123"
    )
    
    # List pending requests
    pending = request_repo.list_pending_requests()
    
    # Update status
    request_repo.update_request_status("TRADE001", "approved")
    
    # Record execution
    exec_repo = TradeExecutionRepository(session)
    execution = exec_repo.record_execution(
        trade_request_id=trade_request.id,
        symbol="AAPL",
        action="BUY",
        quantity=10,
        execution_price=150.50,
        status="Filled",
        order_id="IBKR123"
    )
```

## Database Tables

Tables are automatically created when the models are imported:
- `trade_requests`
- `trade_executions`

Both tables are created in the same SQLite database (`data/fuggerbot.db`).

## Status Values

**TradeRequest.status:**
- `pending`: Awaiting approval
- `approved`: Approved, ready for execution
- `rejected`: Rejected by user
- `expired`: Request expired

**TradeExecution.status:**
- `Filled`: Order completely filled
- `PartiallyFilled`: Order partially filled
- `Submitted`: Order submitted to broker
- `Rejected`: Order rejected by broker
- Other broker-specific statuses










