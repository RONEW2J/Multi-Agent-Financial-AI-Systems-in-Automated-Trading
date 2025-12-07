from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import httpx
import logging
import pandas as pd
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.database import get_db
from app.core.config import settings
from app.models.stock import StockPrice

logger = logging.getLogger(__name__)

router = APIRouter()

executor = ThreadPoolExecutor(max_workers=4)


class MassiveAPIClient:
    BASE_URL = "https://api.massive.com/v1"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_daily_ohlc(self, symbol: str, date: str) -> dict:
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


async def save_stock_data(db: AsyncSession, stock_data: dict) -> StockPrice:
    # if record already exists
    stmt = select(StockPrice).where(
        StockPrice.symbol == stock_data.get("symbol"),
        StockPrice.date == stock_data.get("from")
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        # update existing record
        existing.open = stock_data.get("open")
        existing.high = stock_data.get("high")
        existing.low = stock_data.get("low")
        existing.close = stock_data.get("close")
        existing.volume = stock_data.get("volume")
        existing.after_hours = stock_data.get("afterHours")
        existing.pre_market = stock_data.get("preMarket")
        existing.status = stock_data.get("status")
        existing.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        stock = StockPrice(
            symbol=stock_data.get("symbol"),
            date=stock_data.get("from"),
            open=stock_data.get("open"),
            high=stock_data.get("high"),
            low=stock_data.get("low"),
            close=stock_data.get("close"),
            volume=stock_data.get("volume"),
            after_hours=stock_data.get("afterHours"),
            pre_market=stock_data.get("preMarket"),
            status=stock_data.get("status")
        )
        db.add(stock)
        await db.commit()
        await db.refresh(stock)
        return stock


@router.get("/stock/{symbol}/latest")
async def get_latest_stock_data(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(StockPrice).where(
        StockPrice.symbol == symbol.upper()
    ).order_by(desc(StockPrice.date)).limit(1)
    
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
    stmt = select(StockPrice).where(
        StockPrice.symbol == symbol.upper()
    ).order_by(desc(StockPrice.date)).limit(limit)
    
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
        StockPrice.symbol,
        func.max(StockPrice.date).label('max_date')
    ).group_by(StockPrice.symbol).subquery()
    
    stmt = select(StockPrice).join(
        subquery,
        (StockPrice.symbol == subquery.c.symbol) & 
        (StockPrice.date == subquery.c.max_date)
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
        stock_data = await client.get_daily_ohlc(symbol.upper(), date)
        stock = await save_stock_data(db, stock_data)
        return {
            "message": f"Successfully fetched and saved data for {symbol}",
            "data": stock.to_dict()
        }
    finally:
        await client.close()


@router.get("/stock/csv/available")
async def get_available_csv_symbols():
    dataset_path = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
    
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset directory not found")
    
    try:
        csv_files = list(dataset_path.glob("*.csv"))

        symbols = sorted([f.stem for f in csv_files])
        
        return {
            "count": len(symbols),
            "symbols": symbols
        }
    except Exception as e:
        logger.error(f"Error reading CSV directory: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading CSV directory: {str(e)}")


def _read_stock_csv(symbol: str, dataset_path: Path) -> Optional[dict]:
    try:
        csv_path = dataset_path / f"{symbol}.csv"
        if not csv_path.exists():
            return None
        
        df = pd.read_csv(csv_path)
        if df.empty:
            return None
        
        # Get latest data
        latest = df.iloc[-1]
        first = df.iloc[0]
        
        # Calculate statistics
        close_price = float(latest['close'])
        open_price = float(latest['open'])
        high_price = float(latest['high'])
        low_price = float(latest['low'])
        volume = int(latest.get('volume', 0))
        
        # Calculate change
        if len(df) > 1:
            prev_close = float(df.iloc[-2]['close'])
            change = close_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        else:
            change = 0
            change_pct = 0
        
        # Calculate 52-week high/low
        recent_df = df.tail(252)
        week_52_high = float(recent_df['high'].max())
        week_52_low = float(recent_df['low'].min())
        
        # Calculate average volume
        avg_volume = int(df['volume'].tail(20).mean()) if 'volume' in df.columns else 0
        
        return {
            'symbol': symbol,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'week_52_high': week_52_high,
            'week_52_low': week_52_low,
            'avg_volume': avg_volume,
            'total_records': len(df),
            'first_date': str(first.get('date', '')),
            'last_date': str(latest.get('date', ''))
        }
    except Exception as e:
        logger.error(f"Error reading CSV for {symbol}: {e}")
        return None


@router.get("/stocks/all")
async def get_all_stocks_data(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=10, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by symbol"),
    sort_by: str = Query("symbol", description="Sort by field"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    min_change_pct: Optional[float] = Query(None, description="Minimum change % filter"),
    max_change_pct: Optional[float] = Query(None, description="Maximum change % filter"),
    db: AsyncSession = Depends(get_db),
):
    try:
        subquery = select(
            StockPrice.symbol,
            func.max(StockPrice.date).label('max_date')
        ).group_by(StockPrice.symbol).subquery()
        
        stmt = select(StockPrice).join(
            subquery,
            and_(
                StockPrice.symbol == subquery.c.symbol,
                StockPrice.date == subquery.c.max_date
            )
        )
        
        result = await db.execute(stmt)
        db_stocks = result.scalars().all()
        
        source = "database"
        stocks = []
        
        if db_stocks and len(db_stocks) > 0:
            for stock in db_stocks:
                prev_stmt = select(StockPrice).where(
                    StockPrice.symbol == stock.symbol,
                    StockPrice.date < stock.date
                ).order_by(desc(StockPrice.date)).limit(1)
                prev_result = await db.execute(prev_stmt)
                prev_stock = prev_result.scalar_one_or_none()
                
                close_price = float(stock.close)
                if prev_stock:
                    prev_close = float(prev_stock.close)
                    change = close_price - prev_close
                    change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                else:
                    change = 0
                    change_pct = 0
                
                stocks.append({
                    'symbol': stock.symbol,
                    'open': float(stock.open) if stock.open else 0,
                    'high': float(stock.high) if stock.high else 0,
                    'low': float(stock.low) if stock.low else 0,
                    'close': close_price,
                    'volume': int(stock.volume) if stock.volume else 0,
                    'change': round(change, 2),
                    'change_pct': round(change_pct, 2),
                    'week_52_high': close_price,  # Placeholder
                    'week_52_low': close_price,   # Placeholder
                    'avg_volume': int(stock.volume) if stock.volume else 0,
                    'total_records': 1,
                    'first_date': str(stock.date),
                    'last_date': str(stock.date),
                    'source': 'database'
                })
        else:
            source = "csv"
            dataset_path = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
            
            if not dataset_path.exists():
                raise HTTPException(status_code=404, detail="No data available (DB empty, CSV not found)")
            
            csv_files = list(dataset_path.glob("*.csv"))
            all_symbols = sorted([f.stem for f in csv_files])
            
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, _read_stock_csv, symbol, dataset_path)
                for symbol in all_symbols
            ]
            results = await asyncio.gather(*tasks)
            stocks = [r for r in results if r is not None]
            for s in stocks:
                s['source'] = 'csv'

        if search:
            search_upper = search.upper()
            stocks = [s for s in stocks if search_upper in s['symbol'].upper()]

        if min_price is not None:
            stocks = [s for s in stocks if s['close'] >= min_price]
        if max_price is not None:
            stocks = [s for s in stocks if s['close'] <= max_price]
        if min_change_pct is not None:
            stocks = [s for s in stocks if s['change_pct'] >= min_change_pct]
        if max_change_pct is not None:
            stocks = [s for s in stocks if s['change_pct'] <= max_change_pct]

        reverse = sort_order.lower() == 'desc'
        if sort_by in ['symbol', 'close', 'change', 'change_pct', 'volume', 'week_52_high', 'week_52_low']:
            stocks = sorted(stocks, key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)
        
        total_count = len(stocks)

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_stocks = stocks[start_idx:end_idx]
        
        return {
            'stocks': paginated_stocks,
            'source': source,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        }
    except Exception as e:
        logger.error(f"Error getting all stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/csv/{symbol}")
async def get_stock_csv_data(
    symbol: str,
    days: int = Query(365, ge=1, le=10000, description="Number of days of history"),
    db: AsyncSession = Depends(get_db)
):
    symbol = symbol.upper()
    
    stmt = select(StockPrice).where(
        StockPrice.symbol == symbol
    ).order_by(desc(StockPrice.date)).limit(days)
    
    result = await db.execute(stmt)
    db_records = result.scalars().all()
    
    if db_records and len(db_records) > 0:
        records = [r.to_dict() for r in reversed(db_records)]  # Oldest first
        latest = db_records[0]  # Most recent
        close_price = float(latest.close)
        
        if len(db_records) > 1:
            prev_close = float(db_records[1].close)
            change = close_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        else:
            change = 0
            change_pct = 0
        
        return {
            'symbol': symbol,
            'source': 'database',
            'current_price': close_price,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'total_records': len(records),
            'history': records
        }

    dataset_path = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
    csv_path = dataset_path / f"{symbol}.csv"
    
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Get last N days
        df = df.tail(days)
        
        # Convert to list of dicts
        records = df.to_dict('records')
        
        # Get summary stats
        latest = df.iloc[-1]
        close_price = float(latest['close'])
        
        if len(df) > 1:
            prev_close = float(df.iloc[-2]['close'])
            change = close_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        else:
            change = 0
            change_pct = 0
        
        return {
            'symbol': symbol,
            'source': 'csv',
            'current_price': close_price,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'total_records': len(records),
            'history': records
        }
    except Exception as e:
        logger.error(f"Error reading CSV for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
