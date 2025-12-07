from fastapi import APIRouter
from app.api.market_data_api import router as market_data_router
from app.api.trading_api import router as trading_router
from app.api.portfolio_api import router as portfolio_router
from app.api.user_api import router as user_router

router = APIRouter()

router.include_router(market_data_router, prefix="/market", tags=["Market Data"])
router.include_router(trading_router, prefix="/trading", tags=["Trading"])
router.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio Management"])
router.include_router(user_router, prefix="/users", tags=["Users"])
