from fastapi import APIRouter
from app.api.market_data_api import router as market_data_router

router = APIRouter()

router.include_router(market_data_router, prefix="/market", tags=["Market Data"])
