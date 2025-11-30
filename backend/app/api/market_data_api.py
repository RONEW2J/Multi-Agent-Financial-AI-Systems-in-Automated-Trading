from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timedelta
import httpx
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models.stock_ohlc import StockOHLC

logger = logging.getLogger(__name__)

router = APIRouter()


class MassiveAPIClient:
    BASE_URL = "https://api.massive.com/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_daily_ohlc(self, symbol: str, date: str) -> dict:
        """
        Fetch daily OHLC data for a stock symbol
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with OHLC data
        """
        url = f"{self.BASE_URL}/open-close/{symbol}/{date}"
        params = {
            "adjusted": "true",
            "apiKey": self.api_key
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching data for {symbol} on {date}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch data from Massive API: {str(e)}")
    
    async def close(self):
        await self.client.aclose()


async def save_ohlc_data(db: AsyncSession, ohlc_data: dict) -> StockOHLC:
    # if record already exists
    stmt = select(StockOHLC).where(
        StockOHLC.symbol == ohlc_data.get("symbol"),
        StockOHLC.date == ohlc_data.get("from")
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        # update existing record
        existing.open = ohlc_data.get("open")
        existing.high = ohlc_data.get("high")
        existing.low = ohlc_data.get("low")
        existing.close = ohlc_data.get("close")
        existing.volume = ohlc_data.get("volume")
        existing.after_hours = ohlc_data.get("afterHours")
        existing.pre_market = ohlc_data.get("preMarket")
        existing.status = ohlc_data.get("status")
        existing.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        stock_ohlc = StockOHLC(
            symbol=ohlc_data.get("symbol"),
            date=ohlc_data.get("from"),
            open=ohlc_data.get("open"),
            high=ohlc_data.get("high"),
            low=ohlc_data.get("low"),
            close=ohlc_data.get("close"),
            volume=ohlc_data.get("volume"),
            after_hours=ohlc_data.get("afterHours"),
            pre_market=ohlc_data.get("preMarket"),
            status=ohlc_data.get("status")
        )
        db.add(stock_ohlc)
        await db.commit()
        await db.refresh(stock_ohlc)
        return stock_ohlc


@router.get("/stock/{symbol}/latest")
async def get_latest_stock_data(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(StockOHLC).where(
        StockOHLC.symbol == symbol.upper()
    ).order_by(desc(StockOHLC.date)).limit(1)
    
    result = await db.execute(stmt)
    stock_data = result.scalar_one_or_none()
    
    if not stock_data:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
    
    return stock_data.to_dict()


@router.get("/stock/{symbol}/history")
async def get_stock_history(
    symbol: str,
    limit: int = 30,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(StockOHLC).where(
        StockOHLC.symbol == symbol.upper()
    ).order_by(desc(StockOHLC.date)).limit(limit)
    
    result = await db.execute(stmt)
    stock_data = result.scalars().all()
    
    if not stock_data:
        raise HTTPException(status_code=404, detail=f"No data found for symbol {symbol}")
    
    return [data.to_dict() for data in stock_data]


@router.get("/stocks/latest")
async def get_all_latest_stocks(
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func
    
    subquery = select(
        StockOHLC.symbol,
        func.max(StockOHLC.date).label('max_date')
    ).group_by(StockOHLC.symbol).subquery()
    
    stmt = select(StockOHLC).join(
        subquery,
        (StockOHLC.symbol == subquery.c.symbol) & 
        (StockOHLC.date == subquery.c.max_date)
    )
    
    result = await db.execute(stmt)
    stocks = result.scalars().all()
    
    return [stock.to_dict() for stock in stocks]


@router.post("/stock/{symbol}/fetch")
async def fetch_and_save_stock_data(
    symbol: str,
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    if not hasattr(settings, 'MASSIVE_API_KEY') or not settings.MASSIVE_API_KEY:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")
    
    if not date:
        # default to yesterday (most recent complete trading day)
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    client = MassiveAPIClient(settings.MASSIVE_API_KEY)
    
    try:
        ohlc_data = await client.get_daily_ohlc(symbol.upper(), date)
        stock = await save_ohlc_data(db, ohlc_data)
        return {
            "message": f"Successfully fetched and saved data for {symbol}",
            "data": stock.to_dict()
        }
    finally:
        await client.close()
