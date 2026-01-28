"""Stock data models for financial time-series data."""

from sqlalchemy import Column, String, Float, BigInteger, DateTime, Boolean, Integer
from sqlalchemy.sql import func
from src.models.database import Base


class Stock(Base):
    """Stock metadata model."""
    
    __tablename__ = "stocks"
    
    stock_code = Column(String(10), primary_key=True)
    stock_name = Column(String(50), nullable=False)
    exchange = Column(String(10), nullable=False)  # SH, SZ
    is_st = Column(Boolean, default=False, nullable=False)
    list_date = Column(DateTime)
    industry = Column(String(50))
    market_cap = Column(BigInteger)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DailyQuote(Base):
    """
    Daily price quote model with time-series optimization.
    
    This table will be converted to a TimescaleDB hypertable
    partitioned by the 'date' column.
    """
    
    __tablename__ = "daily_quotes"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)  # Partition key for TimescaleDB
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    amount = Column(Float, nullable=False)  # Trading amount in currency
    
    # Forward adjustment factor for price adjustments
    adjust_factor = Column(Float, default=1.0, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Composite index for efficient queries
    __table_args__ = (
        {'schema': 'public'}
    )


class FetchHistory(Base):
    """Track data fetch operations."""
    
    __tablename__ = "fetch_history"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    fetch_type = Column(String(20), nullable=False)  # scheduled, manual
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(20), nullable=False)  # running, success, failed
    stocks_processed = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    error_message = Column(String(500))
    
    created_at = Column(DateTime, server_default=func.now())
