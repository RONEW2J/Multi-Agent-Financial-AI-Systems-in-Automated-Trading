import logging
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.portfolio_decision_agent import portfolio_decision_agent
from app.agents.market_agent import market_monitor
from app.agents.execution_agent import execution_agent
from app.schemas.portfolio import AnalyzeRequest, DiscoverRequest, UserPortfolio
from app.core.database import get_db
from app.models.stock import StockPrice

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portfolio"])


async def get_current_price_from_db(db: AsyncSession, symbol: str) -> Optional[float]:
    """Get the latest price for a symbol from database"""
    stmt = select(StockPrice).where(
        StockPrice.symbol == symbol
    ).order_by(desc(StockPrice.date)).limit(1)
    result = await db.execute(stmt)
    stock = result.scalar_one_or_none()
    if stock:
        return float(stock.close)
    return None


async def get_current_price_from_csv(symbol: str, dataset_dir: Path) -> Optional[float]:
    """Fallback: Get price from CSV file"""
    csv_path = dataset_dir / f"{symbol}.csv"
    if csv_path.exists():
        import pandas as pd
        df = pd.read_csv(csv_path)
        if not df.empty:
            close_col = 'close' if 'close' in df.columns else 'Close'
            if close_col in df.columns:
                return float(df[close_col].iloc[-1])
    return None


@router.post("/analyze")
async def analyze_portfolio(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        portfolio = request.portfolio
        
        dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        current_prices = {}
        
        # Priority: Database first, CSV as fallback
        for symbol in portfolio.positions.keys():
            # Try database first
            price = await get_current_price_from_db(db, symbol)
            if price is not None:
                current_prices[symbol] = price
                logger.info(f"Got price for {symbol} from database: ${price:.2f}")
            else:
                # Fallback to CSV
                price = await get_current_price_from_csv(symbol, dataset_dir)
                if price is not None:
                    current_prices[symbol] = price
                    logger.info(f"Got price for {symbol} from CSV: ${price:.2f}")
                else:
                    logger.warning(f"No price data found for {symbol}")
        
        health = portfolio_decision_agent.analyze_portfolio_health(
            portfolio.positions,
            current_prices,
            portfolio.cash
        )
        
        # Per-position recommendations
        position_recommendations = []
        
        for symbol, position in portfolio.positions.items():
            # Check if we have data in DB or CSV
            has_db_data = await get_current_price_from_db(db, symbol) is not None
            csv_path = dataset_dir / f"{symbol}.csv"
            has_csv_data = csv_path.exists()
            
            if not has_db_data and not has_csv_data:
                position_recommendations.append({
                    'symbol': symbol,
                    'action': 'HOLD',
                    'reason': 'No data available',
                    'confidence': 0.0
                })
                continue
            
            try:
                # Use database data if available, otherwise CSV
                if has_db_data:
                    prediction = await market_monitor.predict_price_movement_from_db(
                        symbol,
                        db
                    )
                else:
                    prediction = await market_monitor.predict_price_movement_from_csv(
                        symbol,
                        str(csv_path)
                    )
                
                decision = portfolio_decision_agent.make_decision_with_portfolio(
                    prediction,
                    portfolio.positions,
                    portfolio.cash,
                    current_prices
                )
                
                # Add position context
                current_price = current_prices.get(symbol, position['avg_price'])
                return_pct = ((current_price - position['avg_price']) / position['avg_price']) * 100
                
                # Get technical indicators from prediction
                tech_indicators = prediction.get('technical_indicators', {})
                
                position_recommendations.append({
                    'symbol': symbol,
                    'action': decision['action'],
                    'reason': decision['reason'],
                    'confidence': decision['confidence'],
                    'shares': decision.get('shares', 0),
                    'current_return': return_pct,
                    'current_price': current_price,
                    'avg_price': position['avg_price'],
                    'position_value': position['shares'] * current_price,
                    'position_shares': position['shares'],
                    'predicted_change': prediction.get('predicted_change_percent', 0),
                    'predicted_price': prediction.get('predicted_price', current_price),
                    'direction': prediction.get('direction', 'STABLE'),
                    'technical_indicators': tech_indicators,
                    'data_source': 'database' if has_db_data else 'csv'
                })
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                position_recommendations.append({
                    'symbol': symbol,
                    'action': 'HOLD',
                    'reason': f'Analysis error: {str(e)}',
                    'confidence': 0.0
                })
        
        # analyze new opportunities if requested
        new_opportunities = []
        if request.analyze_new_opportunities:
            # Get symbols from database that are not in portfolio
            from sqlalchemy import distinct
            stmt = select(distinct(StockPrice.symbol))
            result = await db.execute(stmt)
            db_symbols = [row[0] for row in result.fetchall()]
            
            # Also check CSV files
            csv_files = list(dataset_dir.glob("*.csv"))
            csv_symbols = [f.stem for f in csv_files]
            
            # Combine and exclude portfolio symbols
            all_symbols = list(set(db_symbols + csv_symbols) - set(portfolio.positions.keys()))
            sample_symbols = all_symbols[:10]
            
            for symbol in sample_symbols:
                try:
                    # Check if in database
                    has_db_data = symbol in db_symbols
                    
                    if has_db_data:
                        prediction = await market_monitor.predict_price_movement_from_db(
                            symbol,
                            db
                        )
                    else:
                        csv_path = dataset_dir / f"{symbol}.csv"
                        prediction = await market_monitor.predict_price_movement_from_csv(
                            symbol,
                            str(csv_path)
                        )
                    
                    decision = portfolio_decision_agent.make_decision_with_portfolio(
                        prediction,
                        portfolio.positions,
                        portfolio.cash,
                        current_prices
                    )
                    
                    if decision['action'] == 'BUY' and decision['confidence'] > 0.5:
                        new_opportunities.append({
                            'symbol': symbol,
                            'predicted_change': prediction.get('predicted_change_percent', 0),
                            'confidence': decision['confidence'],
                            'reason': decision['reason'],
                            'recommended_shares': decision.get('shares', 0),
                            'current_price': prediction.get('current_price', 0),
                            'predicted_price': prediction.get('predicted_price', 0),
                            'direction': prediction.get('direction', 'STABLE'),
                            'technical_indicators': prediction.get('technical_indicators', {}),
                            'data_source': 'database' if has_db_data else 'csv'
                        })
                    # Also add HOLD opportunities with high predicted change
                    elif prediction.get('predicted_change_percent', 0) > 2 and decision['confidence'] > 0.5:
                        new_opportunities.append({
                            'symbol': symbol,
                            'predicted_change': prediction.get('predicted_change_percent', 0),
                            'confidence': decision['confidence'],
                            'reason': f"Potential opportunity: {prediction.get('predicted_change_percent', 0):.1f}% predicted",
                            'recommended_shares': 0,
                            'current_price': prediction.get('current_price', 0),
                            'predicted_price': prediction.get('predicted_price', 0),
                            'direction': prediction.get('direction', 'STABLE'),
                            'technical_indicators': prediction.get('technical_indicators', {}),
                            'data_source': 'database' if has_db_data else 'csv'
                        })
                
                except Exception as e:
                    logger.error(f"Error analyzing new opportunity {symbol}: {e}")
        
        return {
            'status': 'success',
            'portfolio_health': health,
            'position_recommendations': position_recommendations,
            'new_opportunities': sorted(
                new_opportunities,
                key=lambda x: x['confidence'],
                reverse=True
            )[:5]  # Top 5 opportunities
        }
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover")
async def discover_similar_stocks(
    request: DiscoverRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        
        # Get symbols from database first
        from sqlalchemy import distinct
        stmt = select(distinct(StockPrice.symbol))
        result = await db.execute(stmt)
        db_symbols = [row[0] for row in result.fetchall()]
        
        # Also check CSV files for fallback
        csv_files = list(dataset_dir.glob("*.csv"))
        csv_symbols = [f.stem for f in csv_files]
        
        # Use DB symbols primarily, CSV as fallback
        all_symbols = list(set(db_symbols + csv_symbols))
        
        similar_stocks = await market_monitor.find_similar_to_portfolio(
            request.portfolio_symbols,
            all_symbols,
            dataset_dir,
            top_n=request.top_n
        )
        
        # Enrich with predictions
        enriched_recommendations = []
        
        for stock in similar_stocks:
            symbol = stock['symbol']
            
            try:
                # Try database first
                if symbol in db_symbols:
                    prediction = await market_monitor.predict_price_movement_from_db(
                        symbol,
                        db
                    )
                    data_source = 'database'
                else:
                    csv_path = dataset_dir / f"{symbol}.csv"
                    prediction = await market_monitor.predict_price_movement_from_csv(
                        symbol,
                        str(csv_path)
                    )
                    data_source = 'csv'
                
                enriched_recommendations.append({
                    **stock,
                    'predicted_change': prediction.get('predicted_change_percent', 0),
                    'prediction_confidence': prediction.get('confidence', 0),
                    'direction': prediction.get('direction', 'STABLE'),
                    'data_source': data_source
                })
                
            except Exception as e:
                logger.error(f"Error getting prediction for {symbol}: {e}")
                enriched_recommendations.append(stock)
        
        return {
            'status': 'success',
            'recommendations': enriched_recommendations
        }
        
    except Exception as e:
        logger.error(f"Stock discovery error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/{user_id}")
async def get_risk_metrics(user_id: str):
    """
    Calculate risk metrics for user portfolio
    
    TODO: Implement after user authentication is added
    """
    return {
        'status': 'not_implemented',
        'message': 'Risk metrics will be available after user authentication'
    }
