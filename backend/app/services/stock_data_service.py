import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import StockPrice, TrackedStock

logger = logging.getLogger(__name__)

TRACKED_STOCKS = [
    "AAPL",    # Apple
    "MSFT",    # Microsoft
    "AMZN",    # Amazon
    "GOOGL",   # Alphabet (Google)
    "META",    # Meta (Facebook)
    "TSLA",    # Tesla
    "NVDA",    # NVIDIA
    "JPM",     # JPMorgan Chase
    "V",       # Visa
    "WMT",     # Walmart
    "JNJ",     # Johnson & Johnson
    "PG",      # Procter & Gamble
    "MA",      # Mastercard
    "UNH",     # UnitedHealth
    "HD",      # Home Depot
]


class StockDataService:
    @staticmethod
    async def initialize_tracked_stocks(db: AsyncSession):
        try:
            for symbol in TRACKED_STOCKS:
                # Check if already exists
                query = select(TrackedStock).where(TrackedStock.symbol == symbol)
                result = await db.execute(query)
                existing = result.scalar_one_or_none()
                
                if not existing:
                    tracked = TrackedStock(symbol=symbol, is_active=True)
                    db.add(tracked)
                    logger.info(f"Added tracked stock: {symbol}")
            
            await db.commit()
            logger.info(f"Initialized {len(TRACKED_STOCKS)} tracked stocks")
            
        except Exception as e:
            logger.error(f"Error initializing tracked stocks: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def load_stock_data_from_csv(db: AsyncSession, symbol: str, days: Optional[int] = None) -> int:
        dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        csv_path = dataset_dir / f"{symbol}.csv"
        
        if not csv_path.exists():
            logger.warning(f"CSV file not found for {symbol}")
            return 0
        
        try:
            df = pd.read_csv(csv_path)
            
            # Normalize column names
            df.columns = df.columns.str.lower()

            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # Filter to last N days if specified
            if days is not None:
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                df = df[df['date'] >= cutoff_date]
            
            # Sort by date
            df = df.sort_values('date')
            
            if 'volume' not in df.columns:
                df['volume'] = 1000000

            existing_query = select(func.count(StockPrice.id)).where(StockPrice.symbol == symbol)
            existing_result = await db.execute(existing_query)
            existing_count = existing_result.scalar() or 0
            
            if existing_count >= len(df):
                logger.info(f"{symbol}: Already has {existing_count} records, skipping")
                return 0
            
            delete_stmt = delete(StockPrice).where(StockPrice.symbol == symbol)
            await db.execute(delete_stmt)
            
            count = 0
            batch_size = 500
            
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i+batch_size]
                
                for _, row in batch.iterrows():
                    stock_price = StockPrice(
                        symbol=symbol,
                        date=row['date'],
                        open=float(row['open']),
                        high=float(row['high']),
                        low=float(row['low']),
                        close=float(row['close']),
                        volume=int(row['volume']),
                        status='OK'
                    )
                    db.add(stock_price)
                    count += 1
                
                await db.commit()
            
            logger.info(f"Loaded {count} records for {symbol}")
            return count
            
        except Exception as e:
            logger.error(f"Error loading data for {symbol}: {e}")
            await db.rollback()
            return 0
    
    @staticmethod
    async def load_all_tracked_stocks(db: AsyncSession, days: Optional[int] = None):
        logger.info(f"Loading historical data for {len(TRACKED_STOCKS)} tracked stocks (days={'all' if days is None else days})...")
        
        total_loaded = 0
        for symbol in TRACKED_STOCKS:
            count = await StockDataService.load_stock_data_from_csv(db, symbol, days)
            total_loaded += count
        
        logger.info(f"Finished loading {total_loaded} total records for tracked stocks")
    
    @staticmethod
    async def load_all_available_stocks(db: AsyncSession, days: Optional[int] = None):
        dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        
        if not dataset_dir.exists():
            logger.error(f"Dataset directory not found: {dataset_dir}")
            return
        
        csv_files = list(dataset_dir.glob("*.csv"))
        symbols = sorted([f.stem for f in csv_files])
        
        logger.info(f"Loading historical data for ALL {len(symbols)} stocks (days={'all' if days is None else days})...")
        
        total_loaded = 0
        loaded_count = 0
        
        for i, symbol in enumerate(symbols):
            count = await StockDataService.load_stock_data_from_csv(db, symbol, days)
            if count > 0:
                total_loaded += count
                loaded_count += 1
            
            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i + 1}/{len(symbols)} stocks processed, {total_loaded} records loaded")
        
        logger.info(f"Finished loading {total_loaded} total records for {loaded_count} stocks")
    
    @staticmethod
    async def update_stock_prices(db: AsyncSession):
        try:
            query = select(TrackedStock).where(TrackedStock.is_active == True)
            result = await db.execute(query)
            tracked_stocks = result.scalars().all()
            
            dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
            
            updated_count = 0
            for tracked in tracked_stocks:
                symbol = tracked.symbol
                csv_path = dataset_dir / f"{symbol}.csv"
                
                if not csv_path.exists():
                    logger.warning(f"CSV file not found for {symbol}")
                    continue
                
                try:
                    df = pd.read_csv(csv_path)
                    df.columns = df.columns.str.lower()
                    
                    if df.empty:
                        continue
                    
                    latest = df.iloc[-1]
                    date_str = pd.to_datetime(latest['date']).strftime('%Y-%m-%d')
                    
                    # Check if this date already exists
                    query = select(StockPrice).where(
                        StockPrice.symbol == symbol,
                        StockPrice.date == date_str
                    )
                    result = await db.execute(query)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Update existing record
                        existing.open = float(latest['open'])
                        existing.high = float(latest['high'])
                        existing.low = float(latest['low'])
                        existing.close = float(latest['close'])
                        existing.volume = int(latest.get('volume', 1000000))
                    else:
                        stock_price = StockPrice(
                            symbol=symbol,
                            date=date_str,
                            open=float(latest['open']),
                            high=float(latest['high']),
                            low=float(latest['low']),
                            close=float(latest['close']),
                            volume=int(latest.get('volume', 1000000)),
                            status='OK'
                        )
                        db.add(stock_price)
                    
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error updating {symbol}: {e}")
                    continue
            
            await db.commit()
            logger.info(f"Updated prices for {updated_count} stocks")
            
        except Exception as e:
            logger.error(f"Error in update_stock_prices: {e}")
            await db.rollback()
    
    @staticmethod
    async def get_current_prices(db: AsyncSession, symbols: List[str]) -> Dict[str, float]:
        prices = {}
        
        for symbol in symbols:
            try:
                query = select(StockPrice).where(
                    StockPrice.symbol == symbol
                ).order_by(StockPrice.date.desc()).limit(1)
                
                result = await db.execute(query)
                stock_price = result.scalar_one_or_none()
                
                if stock_price:
                    prices[symbol] = stock_price.close
                else:
                    csv_price = await StockDataService._get_price_from_csv(symbol)
                    if csv_price:
                        prices[symbol] = csv_price
                    else:
                        logger.warning(f"No price data found for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")
        
        return prices
    
    @staticmethod
    async def _get_price_from_csv(symbol: str) -> Optional[float]:
        try:
            csv_path = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks" / f"{symbol}.csv"
            if not csv_path.exists():
                return None
            
            df = pd.read_csv(csv_path)
            if df.empty:
                return None
            
            return float(df.iloc[-1]['close'])
        except Exception as e:
            logger.error(f"Error reading CSV for {symbol}: {e}")
            return None
        
        return prices
    
    @staticmethod
    async def get_historical_prices(
        db: AsyncSession,
        symbol: str,
        days: int = 30
    ) -> List[Dict]:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        query = select(StockPrice).where(
            StockPrice.symbol == symbol,
            StockPrice.date >= cutoff_date
        ).order_by(StockPrice.date.asc())
        
        result = await db.execute(query)
        prices = result.scalars().all()
        
        return [
            {
                'date': p.date.isoformat(),
                'open': p.open,
                'high': p.high,
                'low': p.low,
                'close': p.close,
                'volume': p.volume
            }
            for p in prices
        ]
    
    @staticmethod
    async def get_stock_statistics(db: AsyncSession) -> Dict:
        try:
            # Count total records
            total_query = select(func.count(StockPrice.id))
            total_result = await db.execute(total_query)
            total_count = total_result.scalar()
            
            # Count tracked stocks
            tracked_query = select(func.count(TrackedStock.id)).where(TrackedStock.is_active == True)
            tracked_result = await db.execute(tracked_query)
            tracked_count = tracked_result.scalar()
            
            return {
                'total_price_records': total_count,
                'tracked_stocks': tracked_count,
                'tracked_symbols': TRACKED_STOCKS
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


stock_data_service = StockDataService()
