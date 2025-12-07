import logging
from pathlib import Path
from typing import List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.portfolio_decision_agent import portfolio_decision_agent
from app.agents.market_agent import market_monitor
from app.agents.execution_agent import execution_agent
from app.schemas.portfolio import AnalyzeRequest, DiscoverRequest, UserPortfolio

logger = logging.getLogger(__name__)

router = APIRouter(tags=["portfolio"])

@router.post("/analyze")
async def analyze_portfolio(request: AnalyzeRequest):
    try:
        portfolio = request.portfolio
        
        dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        current_prices = {}
        
        for symbol in portfolio.positions.keys():
            csv_path = dataset_dir / f"{symbol}.csv"
            if csv_path.exists():
                import pandas as pd
                df = pd.read_csv(csv_path)
                if not df.empty:
                    current_prices[symbol] = float(df['Close'].iloc[-1])
        
        health = portfolio_decision_agent.analyze_portfolio_health(
            portfolio.positions,
            current_prices,
            portfolio.cash
        )
        
        # Per-position recommendations
        position_recommendations = []
        
        for symbol, position in portfolio.positions.items():
            csv_path = dataset_dir / f"{symbol}.csv"
            
            if not csv_path.exists():
                position_recommendations.append({
                    'symbol': symbol,
                    'action': 'HOLD',
                    'reason': 'No data available',
                    'confidence': 0.0
                })
                continue
            
            try:
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
                
                position_recommendations.append({
                    'symbol': symbol,
                    'action': decision['action'],
                    'reason': decision['reason'],
                    'confidence': decision['confidence'],
                    'shares': decision.get('shares', 0),
                    'current_return': return_pct,
                    'current_price': current_price,
                    'position_value': position['shares'] * current_price
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
            csv_files = list(dataset_dir.glob("*.csv"))
            all_symbols = [f.stem for f in csv_files if f.stem not in portfolio.positions]
            
            sample_symbols = all_symbols[:10]
            
            for symbol in sample_symbols:
                csv_path = dataset_dir / f"{symbol}.csv"
                
                try:
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
                    
                    if decision['action'] == 'BUY' and decision['confidence'] > 0.7:
                        new_opportunities.append({
                            'symbol': symbol,
                            'predicted_change': prediction.get('predicted_change_percent', 0),
                            'confidence': decision['confidence'],
                            'reason': decision['reason'],
                            'recommended_shares': decision.get('shares', 0)
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
async def discover_similar_stocks(request: DiscoverRequest):
    try:
        dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        
        csv_files = list(dataset_dir.glob("*.csv"))
        all_symbols = [f.stem for f in csv_files]
        
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
            csv_path = dataset_dir / f"{symbol}.csv"
            
            try:
                prediction = await market_monitor.predict_price_movement_from_csv(
                    symbol,
                    str(csv_path)
                )
                
                enriched_recommendations.append({
                    **stock,
                    'predicted_change': prediction.get('predicted_change_percent', 0),
                    'prediction_confidence': prediction.get('confidence', 0),
                    'direction': prediction.get('direction', 'STABLE')
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
