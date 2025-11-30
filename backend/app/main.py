import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_tables
from app.api.routes import router
from app.services.stock_updater import start_stock_updater, stop_stock_updater

logger = logging.getLogger("main")

app = FastAPI(
    title="BackEnd Coordination and Communication Protocols for Multi-Agent Financial AI Systems in Automated Trading",
    description="This backend application facilitates coordination and communication among multiple AI agents in automated trading systems.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    debug=True,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    await create_tables()
    logger.info("Database tables created")
    
    # Start background stock data updater
    await start_stock_updater()
    logger.info("Stock data updater started")
    
app.include_router(router, prefix="/api")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown."""
    logger.info("Coordination API shutting down...")
    
    # Stop background stock data updater
    await stop_stock_updater()
    logger.info("Stock data updater stopped")


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "system": "Multi-Agent Trading System",
        "version": "1.0.0",
        "description": "Event-driven microservices architecture for automated trading",
        "agents": {
            "market": {
                "name": "Market Monitoring Agent",
                "port": 8000,
                "url": settings.MARKET_AGENT_URL,
                "description": "Fetches live market data and computes technical indicators"
            },
            "decision": {
                "name": "Decision-Making Agent",
                "port": 8001,
                "url": settings.DECISION_AGENT_URL,
                "description": "Analyzes market data with AI model and makes trading decisions"
            },
            "execution": {
                "name": "Execution Agent",
                "port": 8002,
                "url": settings.EXECUTION_AGENT_URL,
                "description": "Executes trades and records them in the database"
            },
            "coordination": {
                "name": "Coordination API",
                "port": 8003,
                "url": "http://localhost:8003",
                "description": "Unified API for system monitoring and data access"
            }
        },
        "flow": "Market Agent → Decision Agent → Execution Agent",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Coordination API"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )