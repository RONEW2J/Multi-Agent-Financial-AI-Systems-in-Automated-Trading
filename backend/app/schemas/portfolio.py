from pydantic import BaseModel
from typing import List, Dict


class UserPortfolio(BaseModel):
    user_id: str
    cash: float
    positions: Dict[str, Dict]  # {symbol: {shares, avg_price, buy_date}}


class AnalyzeRequest(BaseModel):
    portfolio: UserPortfolio
    analyze_new_opportunities: bool = True


class DiscoverRequest(BaseModel):
    portfolio_symbols: List[str]
    exclude_sectors: List[str] = []
    top_n: int = 10