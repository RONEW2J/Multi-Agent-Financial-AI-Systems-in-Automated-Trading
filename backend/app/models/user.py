from sqlalchemy import String, Float, Integer, DateTime, BigInteger, Index, ForeignKey, JSON, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.sql import func
from app.core.database import Base
from datetime import datetime
import json

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    portfolio: Mapped["UserPortfolio"] = relationship("UserPortfolio", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
    
class UserPortfolio(Base):
    __tablename__ = "user_portfolios"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    cash: Mapped[float] = mapped_column(Float, nullable=False, default=100000.0)
    positions: Mapped[str] = mapped_column(Text, nullable=False, default="{}") 
    transaction_history: Mapped[str] = mapped_column(Text, nullable=False, default="[]") 
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    user: Mapped["User"] = relationship("User", back_populates="portfolio")
    
    def get_positions_dict(self) -> dict:
        try:
            return json.loads(self.positions) if self.positions else {}
        except:
            return {}
    
    def set_positions_dict(self, positions: dict):
        self.positions = json.dumps(positions)
    
    def get_transactions_list(self) -> list:
        try:
            return json.loads(self.transaction_history) if self.transaction_history else []
        except:
            return []
    
    def set_transactions_list(self, transactions: list):
        self.transaction_history = json.dumps(transactions)
        
    def get_portfolio_value(self, current_prices: dict) -> float:
        positions = self.get_positions_dict()
        invested = sum(
            pos['shares'] * current_prices.get(ticker, pos['avg_price'])
            for ticker, pos in positions.items()
        )
        return self.cash + invested
    
    def get_positions_analysis(self, current_prices: dict) -> list:
        """Analyze all positions with current returns"""
        analysis = []
        positions = self.get_positions_dict()
        
        for ticker, pos in positions.items():
            current_price = current_prices.get(ticker, pos['avg_price'])
            value = pos['shares'] * current_price
            return_pct = ((current_price - pos['avg_price']) / pos['avg_price']) * 100
            
            buy_date = datetime.fromisoformat(pos['buy_date']) if isinstance(pos['buy_date'], str) else pos['buy_date']
            
            analysis.append({
                'ticker': ticker,
                'shares': pos['shares'],
                'avg_price': pos['avg_price'],
                'current_price': current_price,
                'value': value,
                'return': return_pct,
                'days_held': (datetime.now() - buy_date).days
            })
        return analysis
    
    def __repr__(self):
        return f"<UserPortfolio(user_id={self.user_id}, cash=${self.cash:.2f})>"