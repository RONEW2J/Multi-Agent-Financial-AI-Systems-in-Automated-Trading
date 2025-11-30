import asyncio
import csv
import os
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import async_session_maker, create_tables
from app.models.stock_ohlc import StockOHLC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Stocks that will be tracked by API (from TRACKED_STOCKS in stock_updater.py)
API_TRACKED_STOCKS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", 
    "JPM", "V", "WMT", "JNJ", "PG", "MA", "UNH", "HD"
]

# Additional stocks for frontend charts
ADDITIONAL_STOCKS = [
    # Tech giants
    "GOOG", "NFLX", "ADBE", "ORCL", "CSCO", "INTC", "AMD", "CRM", "QCOM",
    # Finance
    "BAC", "C", "GS", "MS", "WFC", "AXP", "BLK",
    # Consumer
    "KO", "PEP", "NKE", "MCD", "SBUX", "DIS", "COST",
    # Healthcare  
    "PFE", "ABBV", "TMO", "ABT", "MRK", "BMY", "AMGN",
    # Energy & Industrial
    "XOM", "CVX", "BA", "CAT", "GE", "MMM", "HON",
]


async def load_csv_to_database(symbol: str, csv_path: Path, days_limit: int = 30) -> int:
    if not csv_path.exists():
        logger.warning(f"CSV file not found: {csv_path}")
        return 0
    
    records = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            all_rows = list(reader)
            
            recent_rows = all_rows[-days_limit:] if len(all_rows) > days_limit else all_rows
            
            for row in recent_rows:
                try:
                    date_str = row.get('Date') or row.get('date') or row.get('timestamp')
                    
                    if not date_str:
                        continue
                    
                    date_str = date_str.split('T')[0] if 'T' in date_str else date_str
                    
                    open_price = float(row.get('Open') or row.get('open') or 0)
                    high_price = float(row.get('High') or row.get('high') or 0)
                    low_price = float(row.get('Low') or row.get('low') or 0)
                    close_price = float(row.get('Close') or row.get('close') or 0)
                    volume = int(float(row.get('Volume') or row.get('volume') or 0))
                    
                    if close_price == 0:
                        continue
                    
                    import random
                    pre_market = round(open_price * random.uniform(0.995, 1.005), 2)
                    after_hours = round(close_price * random.uniform(0.995, 1.005), 2)
                    
                    records.append({
                        'symbol': symbol,
                        'date': date_str,
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume,
                        'pre_market': pre_market,
                        'after_hours': after_hours,
                        'status': 'OK'
                    })
                    
                except (ValueError, KeyError) as e:
                    logger.debug(f"Skipping invalid row for {symbol}: {e}")
                    continue
        
        if records:
            async with async_session_maker() as db:
                inserted = 0
                for record in records:
                    stmt = select(StockOHLC).where(
                        StockOHLC.symbol == record['symbol'],
                        StockOHLC.date == record['date']
                    )
                    result = await db.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if not existing:
                        stock_ohlc = StockOHLC(**record)
                        db.add(stock_ohlc)
                        inserted += 1
                
                await db.commit()
                logger.info(f"{symbol}: Inserted {inserted} new records")
                return inserted
        
        return 0
        
    except Exception as e:
        logger.error(f"Error loading {symbol}: {e}")
        return 0


async def load_all_stocks(stocks_dir: Path, days_limit: int = 30):
    all_stocks = list(set(API_TRACKED_STOCKS + ADDITIONAL_STOCKS))
    
    logger.info(f"Loading data for {len(all_stocks)} stocks...")
    logger.info(f"API Tracked: {len(API_TRACKED_STOCKS)} stocks")
    logger.info(f"Additional for charts: {len(ADDITIONAL_STOCKS)} stocks")
    
    total_inserted = 0
    successful = 0
    
    for symbol in sorted(all_stocks):
        csv_path = stocks_dir / f"{symbol}.csv"
        inserted = await load_csv_to_database(symbol, csv_path, days_limit)
        
        if inserted > 0:
            successful += 1
            total_inserted += inserted
    
    logger.info(f"Successfully loaded {successful}/{len(all_stocks)} stocks")
    logger.info(f"Total records inserted: {total_inserted}")


async def main():
    await create_tables()
    logger.info("Database tables ready")
    
    current_dir = Path(__file__).parent
    stocks_dir = current_dir / "dataset_of_stocks" / "stocks"
    
    if not stocks_dir.exists():
        logger.error(f"Stocks directory not found: {stocks_dir}")
        logger.info("Please ensure dataset_of_stocks/stocks/ directory exists")
        return
    
    logger.info(f"Loading from: {stocks_dir}")
    
    await load_all_stocks(stocks_dir, days_limit=3650)
    
    logger.info("Start backend: python -m app.main")
    logger.info("API Tracked stocks (auto-updated): " + ", ".join(API_TRACKED_STOCKS))
    logger.info("Additional stocks (static data): " + ", ".join(ADDITIONAL_STOCKS[:5]) + "...")
    logger.info("Query all: GET /api/market/stocks/latest")


if __name__ == "__main__":
    asyncio.run(main())
