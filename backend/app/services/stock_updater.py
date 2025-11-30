import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.database import async_session_maker
from app.core.config import settings
from app.api.market_data_api import MassiveAPIClient, save_ohlc_data

logger = logging.getLogger(__name__)


class StockDataUpdater:
    """
    These stocks are updated from Massive API (real-time data).
    """
    
    # list of stock symbols to track via API because of rate limiting on Massive API (5 requests/min)
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
    
    def __init__(self):
        self.is_running = False
        self.api_client = None
        self.current_batch_index = 0
        
    async def initialize(self):
        if not hasattr(settings, 'MASSIVE_API_KEY') or not settings.MASSIVE_API_KEY:
            logger.warning("MASSIVE_API_KEY not configured. Stock data updates will not run.")
            return False
        
        self.api_client = MassiveAPIClient(settings.MASSIVE_API_KEY)
        logger.info("Stock Data Updater initialized")
        return True
    
    async def fetch_and_save_batch(self, symbols: List[str], date: str):
        """
        Args:
            symbols: list of stock symbols (max 5 for rate limiting)
            date: YYYY-MM-DD format
        """
        async with async_session_maker() as db:
            for symbol in symbols:
                try:
                    logger.info(f"Fetching data for {symbol} on {date}")
                    ohlc_data = await self.api_client.get_daily_ohlc(symbol, date)
                    await save_ohlc_data(db, ohlc_data)
                    logger.info(f"Successfully saved data for {symbol}")
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {e}")
                    continue
    
    def get_next_batch(self) -> List[str]:
        """
        Get the next batch of 5 stocks to update.
        Rotates through all tracked stocks.
        """
        batch_size = 5
        total_stocks = len(self.TRACKED_STOCKS)
        
        # calculate the starting index for this batch
        start_idx = self.current_batch_index
        end_idx = start_idx + batch_size
        
        # get the batch (with wrapping)
        if end_idx <= total_stocks:
            batch = self.TRACKED_STOCKS[start_idx:end_idx]
            self.current_batch_index = end_idx % total_stocks
        else:
            # wrap around to the beginning
            batch = self.TRACKED_STOCKS[start_idx:] + self.TRACKED_STOCKS[:end_idx - total_stocks]
            self.current_batch_index = end_idx % total_stocks
        
        return batch
    
    def get_latest_trading_date(self) -> str:
        today = datetime.now()
        
        # start checking from 1 day ago
        for days_back in range(1, 8):
            check_date = today - timedelta(days=days_back)
            
            # skip weekends (Saturday=5, Sunday=6)
            if check_date.weekday() in [5, 6]:
                continue
            
            # return the first weekday we find
            return check_date.strftime("%Y-%m-%d")
        
        # fallback: return 3 days ago
        return (today - timedelta(days=3)).strftime("%Y-%m-%d")
    
    async def update_cycle(self):
        """
        This runs every 5 minutes to respect rate limits.
        """
        # get the most recent likely trading day (skip weekends)
        date = self.get_latest_trading_date()
        
        # get next batch of stocks
        batch = self.get_next_batch()
        
        logger.info(f"Starting update cycle for batch: {batch}")
        logger.info(f"Date: {date}, Batch index: {self.current_batch_index}")
        
        try:
            await self.fetch_and_save_batch(batch, date)
            logger.info(f"Completed update cycle for batch: {batch}")
        except Exception as e:
            logger.error(f"Error in update cycle: {e}")
    
    async def run(self):
        """
        main loop that runs continuously, updating stocks every 5 minutes.
        rotates through all tracked stocks, 5 at a time.
        """
        initialized = await self.initialize()
        if not initialized:
            logger.error("Failed to initialize Stock Data Updater")
            return
        
        self.is_running = True
        logger.info("Stock Data Updater started")
        logger.info(f"Tracking {len(self.TRACKED_STOCKS)} stocks: {', '.join(self.TRACKED_STOCKS)}")
        logger.info("Update interval: 5 minutes per batch (5 stocks)")
        
        try:
            while self.is_running:
                await self.update_cycle()
                
                # wait 5 minutes before next batch (respecting rate limit)
                logger.info("Waiting 5 minutes before next update cycle...")
                await asyncio.sleep(300)
                
        except asyncio.CancelledError:
            logger.info("Stock Data Updater cancelled")
        except Exception as e:
            logger.error(f"Fatal error in Stock Data Updater: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the updater and cleanup"""
        self.is_running = False
        if self.api_client:
            await self.api_client.close()
        logger.info("Stock Data Updater stopped")


stock_updater = StockDataUpdater()


async def start_stock_updater():
    asyncio.create_task(stock_updater.run())
    logger.info("Stock data updater background task created")


async def stop_stock_updater():
    await stock_updater.stop()
