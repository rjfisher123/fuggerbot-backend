"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# SQLite database path
db_path = Path(__file__).parent.parent / "data" / "fuggerbot.db"
db_path.parent.mkdir(parents=True, exist_ok=True)

# Create engine
engine = create_engine(f"sqlite:///{db_path}", echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models to ensure they're registered
from persistence.models_paper import Base as PaperBase
from persistence.models_triggers import Base as TriggerBase
from persistence.models_ibkr import Base as IBKRBase
from persistence.models_trades import Base as TradesBase
from persistence.models_portfolio import Base as PortfolioBase
from persistence.models_backtest import Base as BacktestBase

# Create tables if they don't exist
PaperBase.metadata.create_all(bind=engine)
TriggerBase.metadata.create_all(bind=engine)
IBKRBase.metadata.create_all(bind=engine)
TradesBase.metadata.create_all(bind=engine)
PortfolioBase.metadata.create_all(bind=engine)
BacktestBase.metadata.create_all(bind=engine)

