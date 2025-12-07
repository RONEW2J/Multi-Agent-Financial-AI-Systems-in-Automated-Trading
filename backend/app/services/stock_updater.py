import asyncio
import logging
from contextlib import asynccontextmanager

from app.core.database import async_session_maker
from app.services.stock_data_service import stock_data_service

logger = logging.getLogger(__name__)

_update_task = None
_is_running = False


async def stock_price_updater():
    global _is_running
    
    logger.info("Stock price updater task started")
    
    while _is_running:
        try:
            logger.info("Updating stock prices...")
            
            async with async_session_maker() as db:
                await stock_data_service.update_stock_prices(db)
            
            logger.info("Stock prices updated successfully")
            
            await asyncio.sleep(300)
            
        except asyncio.CancelledError:
            logger.info("Stock price updater task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in stock price updater: {e}")
            await asyncio.sleep(60)


async def initialize_stock_data():
    try:
        logger.info("Initializing stock data...")
        
        async with async_session_maker() as db:
            await stock_data_service.initialize_tracked_stocks(db)

            await stock_data_service.load_all_available_stocks(db, days=None)
        
        logger.info("Stock data initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing stock data: {e}")
        raise


async def start_stock_updater():
    global _update_task, _is_running
    
    if _update_task is not None:
        logger.warning("Stock updater already running")
        return

    await initialize_stock_data()
    
    _is_running = True
    _update_task = asyncio.create_task(stock_price_updater())
    logger.info("Stock price updater started (updates every 5 minutes)")


async def stop_stock_updater():
    global _update_task, _is_running
    
    if _update_task is None:
        return
    
    _is_running = False
    _update_task.cancel()
    
    try:
        await _update_task
    except asyncio.CancelledError:
        pass
    
    _update_task = None
    logger.info("Stock price updater stopped")
