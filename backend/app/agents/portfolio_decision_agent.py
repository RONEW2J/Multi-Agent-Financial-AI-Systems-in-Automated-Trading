import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import cosine
import joblib

logger = logging.getLogger(__name__)


class PortfolioAwareDecisionAgent:
    """
    1. Existing portfolio positions
    2. Portfolio correlations
    3. Diversification
    4. Risk management
    """
    
    def __init__(self, risk_tolerance: float = 0.5):
        self.name = "Portfolio Decision AI"
        self.risk_tolerance = risk_tolerance
        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.decision_model: Optional[GradientBoostingClassifier] = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        self.decision_history: List[Dict] = []
        self.feedback_data: List[Dict] = []
        
        # Sector mapping for diversification
        self.sector_map = self._load_sector_mapping()
    
    def _load_sector_mapping(self) -> Dict[str, str]:
        return {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'AMZN': 'Consumer', 'META': 'Technology', 'TSLA': 'Automotive',
            'JPM': 'Finance', 'BAC': 'Finance', 'WFC': 'Finance',
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
            'XOM': 'Energy', 'CVX': 'Energy', 'KO': 'Consumer',
            'PG': 'Consumer', 'WMT': 'Consumer', 'HD': 'Consumer',
            'V': 'Finance', 'MA': 'Finance', 'NVDA': 'Technology'
        }
    
    def make_decision_with_portfolio(
        self,
        prediction: Dict,
        portfolio_positions: Dict,
        portfolio_cash: float,
        current_prices: Dict
    ) -> Dict:

        symbol = prediction.get('symbol')
        
        if not symbol:
            return self._create_decision('HOLD', 'Invalid prediction data', 0.0)
        
        # Check if stock is already in portfolio
        if symbol in portfolio_positions:
            return self._analyze_existing_position(
                symbol, prediction, portfolio_positions, current_prices
            )
        else:
            return self._analyze_new_opportunity(
                symbol, prediction, portfolio_positions, portfolio_cash, current_prices
            )
    
    def _analyze_existing_position(
        self,
        symbol: str,
        prediction: Dict,
        positions: Dict,
        prices: Dict
    ) -> Dict:
        """Analyze decision for stocks ALREADY in portfolio"""
        position = positions[symbol]
        current_price = prices.get(symbol, position['avg_price'])
        cost_basis = position['avg_price']
        shares = position['shares']
        
        # Calculate current return
        return_pct = ((current_price - cost_basis) / cost_basis) * 100
        days_held = (datetime.now() - datetime.fromisoformat(position['buy_date'])).days
        
        predicted_change = prediction.get('predicted_change_percent', 0)
        confidence = prediction.get('confidence', 0.5)
        direction = prediction.get('direction', 'STABLE')
        
        logger.info(f"{self.name}: Analyzing {symbol} - Current return: {return_pct:.2f}%, Predicted: {predicted_change:.2f}%")
        
        # Decision logic for existing positions
        
        # Strong SELL signals
        if predicted_change < -5 and confidence > 0.7:
            if return_pct > 10:
                return self._create_decision(
                    'SELL', 
                    f'Take profit ({return_pct:.1f}%) before predicted decline ({predicted_change:.1f}%)',
                    confidence,
                    shares  # Sell all shares
                )
            elif return_pct < -10:
                return self._create_decision(
                    'SELL',
                    f'Cut losses ({return_pct:.1f}%) - strong downtrend predicted',
                    confidence,
                    shares
                )
        
        # Average down opportunity
        if predicted_change > 10 and confidence > 0.75 and return_pct < -5:
            return self._create_decision(
                'BUY',
                f'Average down - strong signal ({predicted_change:.1f}%) while at loss ({return_pct:.1f}%)',
                confidence,
                shares // 2  # Buy half of current position
            )
        
        # Add to winners
        if predicted_change > 8 and confidence > 0.8 and return_pct > 5:
            return self._create_decision(
                'BUY',
                f'Add to winning position ({return_pct:.1f}%) - continued growth expected',
                confidence,
                shares // 3  # Buy 1/3 of current position
            )
        
        # Take profit on good gains
        if return_pct > 20 and predicted_change < 3:
            return self._create_decision(
                'SELL',
                f'Take profit - {return_pct:.1f}% gain, momentum slowing',
                0.7,
                shares // 2  # Sell half
            )
        
        # Stop loss
        if return_pct < -15:
            return self._create_decision(
                'SELL',
                f'Stop loss triggered at {return_pct:.1f}%',
                0.9,
                shares
            )
        
        # Hold
        return self._create_decision(
            'HOLD',
            f'Monitor position - {return_pct:.1f}% return, held {days_held} days',
            confidence
        )
    
    def _analyze_new_opportunity(
        self,
        symbol: str,
        prediction: Dict,
        positions: Dict,
        cash: float,
        prices: Dict
    ) -> Dict:
        predicted_change = prediction.get('predicted_change_percent', 0)
        confidence = prediction.get('confidence', 0.5)
        current_price = prices.get(symbol, prediction.get('current_price', 0))
        
        if current_price == 0:
            return self._create_decision('HOLD', 'Price data unavailable', 0.0)
        
        # Check portfolio constraints
        
        # Sector diversification
        symbol_sector = self.sector_map.get(symbol, 'Unknown')
        sector_exposure = self._calculate_sector_exposure(positions, prices, symbol_sector)
        
        if sector_exposure > 0.40:
            return self._create_decision(
                'HOLD',
                f'Over-concentrated in {symbol_sector} sector ({sector_exposure*100:.1f}%)',
                0.3
            )
        
        # Find similar stocks in portfolio
        similar_stocks = self._find_similar_in_portfolio(symbol, positions, prediction)
        
        # Check if we have cash
        max_position_size = cash * 0.10
        if cash < max_position_size:
            return self._create_decision(
                'HOLD',
                'Insufficient cash for new position',
                0.2
            )
        
        # Decision logic for new opportunities
        
        # Strong buy signal
        if predicted_change > 8 and confidence > 0.75:
            shares = int(max_position_size / current_price)
            reason = f'Strong signal: {predicted_change:.1f}% predicted'
            if similar_stocks:
                reason += f', similar to {", ".join(similar_stocks[:2])}'
            
            return self._create_decision('BUY', reason, confidence, shares)
        
        # Moderate buy signal
        if predicted_change > 5 and confidence > 0.65:
            shares = int((max_position_size * 0.5) / current_price)
            return self._create_decision(
                'BUY',
                f'Moderate signal: {predicted_change:.1f}% predicted',
                confidence,
                shares
            )
        
        return self._create_decision(
            'HOLD',
            f'Signal too weak: {predicted_change:.1f}% at {confidence*100:.0f}% confidence',
            confidence
        )
    
    def _calculate_sector_exposure(
        self,
        positions: Dict,
        prices: Dict,
        target_sector: str
    ) -> float:
        if not positions:
            return 0.0
        
        total_value = 0
        sector_value = 0
        
        for symbol, pos in positions.items():
            price = prices.get(symbol, pos['avg_price'])
            value = pos['shares'] * price
            total_value += value
            
            if self.sector_map.get(symbol, 'Unknown') == target_sector:
                sector_value += value
        
        return sector_value / total_value if total_value > 0 else 0.0
    
    def _find_similar_in_portfolio(
        self,
        symbol: str,
        positions: Dict,
        prediction: Dict
    ) -> List[str]:
        similar = []
        
        symbol_sector = self.sector_map.get(symbol, 'Unknown')
        
        for pos_symbol in positions.keys():
            if self.sector_map.get(pos_symbol, 'Unknown') == symbol_sector:
                similar.append(pos_symbol)
        
        return similar
    
    def _create_decision(
        self,
        action: str,
        reason: str,
        confidence: float,
        shares: int = 0
    ) -> Dict:
        decision = {
            'action': action,
            'reason': reason,
            'confidence': float(confidence),
            'timestamp': datetime.now().isoformat()
        }
        
        if action in ['BUY', 'SELL'] and shares > 0:
            decision['shares'] = shares
        
        self.decision_history.append(decision)
        
        return decision
    
    def analyze_portfolio_health(
        self,
        positions: Dict,
        prices: Dict,
        cash: float
    ) -> Dict:
        if not positions:
            return {
                'status': 'empty',
                'diversification_score': 0,
                'sector_concentration': {},
                'recommendations': ['Start building portfolio with diversified positions']
            }
        
        total_value = cash
        sector_distribution = {}
        winners = []
        losers = []
        
        for symbol, pos in positions.items():
            price = prices.get(symbol, pos['avg_price'])
            value = pos['shares'] * price
            total_value += value
            
            return_pct = ((price - pos['avg_price']) / pos['avg_price']) * 100
            
            sector = self.sector_map.get(symbol, 'Unknown')
            sector_distribution[sector] = sector_distribution.get(sector, 0) + value
            
            if return_pct > 10:
                winners.append({'symbol': symbol, 'return': return_pct})
            elif return_pct < -10:
                losers.append({'symbol': symbol, 'return': return_pct})
        
        # Calculate diversification score
        num_stocks = len(positions)
        num_sectors = len(sector_distribution)
        diversification = min(1.0, (num_stocks * num_sectors) / 20)
        
        # Sector concentration
        sector_pct = {k: (v/total_value)*100 for k, v in sector_distribution.items()}
        
        return {
            'status': 'healthy' if diversification > 0.5 else 'needs_diversification',
            'total_value': total_value,
            'cash_percentage': (cash / total_value) * 100,
            'num_positions': num_stocks,
            'diversification_score': diversification,
            'sector_distribution': sector_pct,
            'top_performers': sorted(winners, key=lambda x: x['return'], reverse=True)[:5],
            'underperformers': sorted(losers, key=lambda x: x['return'])[:5]
        }


portfolio_decision_agent = PortfolioAwareDecisionAgent()
