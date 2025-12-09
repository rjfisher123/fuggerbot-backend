"""Repository classes for account state and portfolio positions."""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from persistence.models_portfolio import AccountState, Position


class AccountStateRepository:
    """Repository for managing account state snapshots."""

    def __init__(self, session: Session):
        self.session = session

    def add_state(
        self,
        cash: float,
        buying_power: float,
        realized_pnl: float,
        unrealized_pnl: float,
        equity: float,
        timestamp: Optional[datetime] = None,
    ) -> AccountState:
        """Insert a new account state snapshot."""
        state = AccountState(
            cash=cash,
            buying_power=buying_power,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            equity=equity,
            timestamp=timestamp or datetime.utcnow(),
        )
        self.session.add(state)
        self.session.commit()
        self.session.refresh(state)
        return state

    def get_latest(self) -> Optional[AccountState]:
        """Get the most recent account state snapshot."""
        return (
            self.session.query(AccountState)
            .order_by(AccountState.timestamp.desc())
            .first()
        )

    def list_history(self, limit: int = 100) -> List[AccountState]:
        """Get recent account state history."""
        return (
            self.session.query(AccountState)
            .order_by(AccountState.timestamp.desc())
            .limit(limit)
            .all()
        )


class PositionRepository:
    """Repository for managing portfolio positions (live)."""

    def __init__(self, session: Session):
        self.session = session

    def list_positions(self) -> List[Position]:
        """List all positions."""
        return self.session.query(Position).all()

    def get_by_symbol(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return (
            self.session.query(Position)
            .filter(Position.symbol == symbol.upper())
            .first()
        )

    def upsert_position(
        self,
        symbol: str,
        quantity: float,
        avg_cost: float,
        market_value: float,
        unrealized_pnl: float,
    ) -> Position:
        """Create or update a position for a symbol."""
        symbol = symbol.upper()
        position = self.get_by_symbol(symbol)

        if position is None:
            position = Position(
                symbol=symbol,
                quantity=quantity,
                avg_cost=avg_cost,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                updated_at=datetime.utcnow(),
            )
            self.session.add(position)
        else:
            position.quantity = quantity
            position.avg_cost = avg_cost
            position.market_value = market_value
            position.unrealized_pnl = unrealized_pnl
            position.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(position)
        return position

    def delete_position(self, symbol: str) -> bool:
        """Delete a position for a symbol."""
        symbol = symbol.upper()
        position = self.get_by_symbol(symbol)
        if not position:
            return False
        self.session.delete(position)
        self.session.commit()
        return True
