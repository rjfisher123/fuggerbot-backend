"""Database-backed portfolio service."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import sessionmaker as SessionMaker

from persistence.models_paper import PaperTrade
from persistence.repositories_paper import PaperTradeRepository, PositionRepository


class PortfolioServiceDB:
    """Service that accesses portfolio data via a database sessionmaker."""

    def __init__(self, sessionmaker: SessionMaker):
        self.sessionmaker = sessionmaker

    def get_positions(self):
        with self.sessionmaker() as session:
            repo = PositionRepository(session)
            return repo.list_positions()

    def get_paper_trades(self):
        with self.sessionmaker() as session:
            repo = PaperTradeRepository(session)
            return repo.list_trades()

    def record_paper_trade(self, symbol: str, side: str, qty: float, price: float):
        with self.sessionmaker() as session:
            repo = PaperTradeRepository(session)
            trade = PaperTrade(
                symbol=symbol,
                side=side,
                quantity=qty,
                price=price,
                timestamp=datetime.utcnow(),
            )
            repo.add_trade(trade)




