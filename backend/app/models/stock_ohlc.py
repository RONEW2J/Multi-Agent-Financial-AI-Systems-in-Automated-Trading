from sqlalchemy import String, Float, Integer, DateTime, BigInteger, Index
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime


class StockOHLC(Base):
    """Model for storing daily OHLC (Open, High, Low, Close) stock data"""
    __tablename__ = "stock_ohlc"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # OHLC data
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    after_hours: Mapped[float] = mapped_column(Float, nullable=True)
    pre_market: Mapped[float] = mapped_column(Float, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    __table_args__ = (
        Index('idx_symbol_date', 'symbol', 'date', unique=True),
    )
    
    def __repr__(self):
        return f"<StockOHLC(symbol={self.symbol}, date={self.date}, close={self.close})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "after_hours": self.after_hours,
            "pre_market": self.pre_market,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
