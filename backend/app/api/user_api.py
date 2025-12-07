"""
User Management API Endpoints
Handles user registration, login, and profile management
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.auth_service import auth_service
from app.services.portfolio_service import portfolio_service
from app.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    LoginResponse,
    BuyStockRequest,
    SellStockRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    token = credentials.credentials
    payload = auth_service.decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    user = await auth_service.get_user_by_id(db, int(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await auth_service.register_user(
            db=db,
            username=request.username,
            email=request.email,
            password=request.password,
            initial_capital=request.initial_capital
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=LoginResponse)
async def login_user(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await auth_service.authenticate_user(
        db=db,
        username=request.username,
        password=request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat()
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/me/portfolio")
async def get_my_portfolio(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        summary = await portfolio_service.get_portfolio_summary(db, current_user.id)
        return {
            'status': 'success',
            'portfolio': summary
        }
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/me/portfolio/buy")
async def buy_stock_for_user(
    request: BuyStockRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        price = request.price
        if price is None or price == 0:
            from app.services.portfolio_service import portfolio_service as ps
            prices = await ps.get_current_prices(db, [request.symbol])
            price = prices.get(request.symbol)
            if price is None:
                raise ValueError(f"Could not fetch current price for {request.symbol}")
        
        result = await portfolio_service.buy_stock(
            db=db,
            user_id=current_user.id,
            symbol=request.symbol,
            shares=request.shares,
            price=price
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error buying stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/me/portfolio/sell")
async def sell_stock_for_user(
    request: SellStockRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        price = request.price
        if price is None or price == 0:
            from app.services.portfolio_service import portfolio_service as ps
            prices = await ps.get_current_prices(db, [request.symbol])
            price = prices.get(request.symbol)
            if price is None:
                raise ValueError(f"Could not fetch current price for {request.symbol}")
        
        result = await portfolio_service.sell_stock(
            db=db,
            user_id=current_user.id,
            symbol=request.symbol,
            shares=request.shares,
            price=price
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error selling stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me/transactions")
async def get_my_transactions(
    limit: int = 50,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        transactions = await portfolio_service.get_transaction_history(
            db, current_user.id, limit
        )
        return {
            'status': 'success',
            'count': len(transactions),
            'transactions': transactions
        }
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/portfolio")
async def get_user_portfolio(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        summary = await portfolio_service.get_portfolio_summary(db, user_id)
        return {
            'status': 'success',
            'portfolio': summary
        }
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
