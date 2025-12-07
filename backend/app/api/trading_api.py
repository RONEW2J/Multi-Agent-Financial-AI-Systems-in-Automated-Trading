from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.trading import TrainingRequest, TradingCycleRequest, SystemStatusResponse, RiskSettingsRequest
from app.core.database import get_db
from app.agents.coordinator import trading_coordinator, TradingCoordinator
from app.api.user_api import get_current_user
from app.models.user import User


router = APIRouter()



@router.post("/train")
async def train_agents(
    request: TrainingRequest,
    session: AsyncSession = Depends(get_db)
):
    try:
        results = await trading_coordinator.train_all_agents(
            session, 
            request.symbols,
            request.use_sample
        )
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cycle/run")
async def run_trading_cycle(
    request: TradingCycleRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Create user-specific coordinator
        user_coordinator = TradingCoordinator(user_id=current_user.id, db_session=session)
        
        result = await user_coordinator.run_trading_cycle(
            session,
            request.symbols,
            request.use_csv,
            request.risk_tolerance
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_system_status(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overall trading system status for authenticated user"""
    try:
        user_coordinator = TradingCoordinator(user_id=current_user.id, db_session=session)
        await user_coordinator.execution_agent.load_trade_stats()
        status = await user_coordinator.get_system_status()
        return {
            "status": "operational",
            "details": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_trading_sessions(limit: int = 10):
    try:
        sessions = trading_coordinator.trading_sessions[-limit:]
        return {
            "total_sessions": len(trading_coordinator.trading_sessions),
            "sessions": sessions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio")
async def get_portfolio(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        user_coordinator = TradingCoordinator(user_id=current_user.id, db_session=session)
        portfolio = await user_coordinator.execution_agent.get_portfolio_summary()
        return portfolio
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        user_coordinator = TradingCoordinator(user_id=current_user.id, db_session=session)
        await user_coordinator.execution_agent.load_trade_stats()
        performance = await user_coordinator.execution_agent.get_performance_metrics()
        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-settings")
async def get_risk_settings():
    try:
        thresholds = trading_coordinator.decision_maker.get_thresholds()
        return {
            "status": "success",
            "settings": thresholds,
            "description": {
                "risk_tolerance": "0.0 = Conservative, 0.5 = Moderate, 1.0 = Aggressive",
                "buy_threshold_percent": "Minimum predicted gain % to trigger BUY",
                "sell_threshold_percent": "Maximum predicted loss % to trigger SELL",
                "min_confidence": "Minimum prediction confidence required"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk-settings")
async def set_risk_settings(request: RiskSettingsRequest):
    try:
        trading_coordinator.decision_maker.set_risk_tolerance(request.risk_tolerance)
        thresholds = trading_coordinator.decision_maker.get_thresholds()
        return {
            "status": "success",
            "message": f"Risk tolerance set to {request.risk_tolerance:.1%}",
            "settings": thresholds
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decisions/history")
async def get_decision_history(limit: int = 20):
    try:
        decisions = trading_coordinator.decision_maker.decision_history[-limit:]
        return {
            "total_decisions": len(trading_coordinator.decision_maker.decision_history),
            "decisions": decisions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/pending")
async def get_pending_feedback():
    try:
        pending = [
            f for f in trading_coordinator.execution_agent.pending_feedback
            if not f["checked"]
        ]
        return {
            "count": len(pending),
            "items": pending
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
