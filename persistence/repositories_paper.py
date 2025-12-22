"""Repositories for paper trading data."""
from __future__ import annotations

from sqlalchemy.orm import Session

from persistence.models_paper import PaperTrade, Position


class PositionRepository:
    """Repository for managing positions."""

    def __init__(self, session: Session):
        self.session = session

    def list_positions(self):
        return self.session.query(Position).all()

    def add_position(self, position: Position):
        self.session.add(position)
        self.session.commit()


class PaperTradeRepository:
    """Repository for managing paper trades."""

    def __init__(self, session: Session):
        self.session = session

    def list_trades(self):
        return (
            self.session.query(PaperTrade)
            .order_by(PaperTrade.timestamp.desc())
            .all()
        )

    def add_trade(self, trade: PaperTrade):
        self.session.add(trade)
        self.session.commit()










