import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserPortfolio

logger = logging.getLogger(__name__)


class UserPortfolioService:
    @staticmethod
    async def get_portfolio(db: AsyncSession, user_id: int) -> Optional[UserPortfolio]:
        query = select(UserPortfolio).where(UserPortfolio.user_id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_current_prices(db: AsyncSession, symbols: List[str]) -> Dict[str, float]:
        from app.services.stock_data_service import stock_data_service
        return await stock_data_service.get_current_prices(db, symbols)
    
    @staticmethod
    async def buy_stock(
        db: AsyncSession,
        user_id: int,
        symbol: str,
        shares: int,
        price: float
    ) -> Dict:
        portfolio = await UserPortfolioService.get_portfolio(db, user_id)
        
        if not portfolio:
            raise ValueError(f"Portfolio not found for user {user_id}")
        
        cost = shares * price
        
        if portfolio.cash < cost:
            raise ValueError(f"Insufficient funds. Need ${cost:.2f}, have ${portfolio.cash:.2f}")

        portfolio.cash -= cost

        positions = portfolio.get_positions_dict()
        
        if symbol in positions:
            # Average down/up
            pos = positions[symbol]
            total_shares = pos['shares'] + shares
            total_cost = (pos['shares'] * pos['avg_price']) + cost
            avg_price = total_cost / total_shares
            
            positions[symbol] = {
                'shares': total_shares,
                'avg_price': avg_price,
                'buy_date': pos['buy_date']  # Keep original buy date
            }
        else:
            positions[symbol] = {
                'shares': shares,
                'avg_price': price,
                'buy_date': datetime.now().isoformat()
            }
        
        portfolio.set_positions_dict(positions)
        
        transactions = portfolio.get_transactions_list()
        transactions.append({
            'type': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total': cost,
            'timestamp': datetime.now().isoformat()
        })
        portfolio.set_transactions_list(transactions)
        
        await db.commit()
        await db.refresh(portfolio)
        
        logger.info(f"User {user_id} bought {shares} shares of {symbol} at ${price:.2f}")
        
        return {
            'status': 'success',
            'action': 'BUY',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total_cost': cost,
            'remaining_cash': portfolio.cash
        }
    
    @staticmethod
    async def sell_stock(
        db: AsyncSession,
        user_id: int,
        symbol: str,
        shares: int,
        price: float
    ) -> Dict:
        portfolio = await UserPortfolioService.get_portfolio(db, user_id)
        
        if not portfolio:
            raise ValueError(f"Portfolio not found for user {user_id}")
        
        positions = portfolio.get_positions_dict()
        
        if symbol not in positions:
            raise ValueError(f"No position in {symbol}")
        
        pos = positions[symbol]
        
        if pos['shares'] < shares:
            raise ValueError(f"Insufficient shares. Have {pos['shares']}, trying to sell {shares}")
        
        revenue = shares * price
        
        # Update cash
        portfolio.cash += revenue
        
        # Update positions
        if pos['shares'] == shares:
            # Sell entire position
            del positions[symbol]
        else:
            # Partial sell
            positions[symbol]['shares'] -= shares
        
        portfolio.set_positions_dict(positions)
        
        # Calculate profit/loss
        profit_loss = revenue - (shares * pos['avg_price'])
        profit_loss_pct = (profit_loss / (shares * pos['avg_price'])) * 100
        
        transactions = portfolio.get_transactions_list()
        transactions.append({
            'type': 'SELL',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total': revenue,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'timestamp': datetime.now().isoformat()
        })
        portfolio.set_transactions_list(transactions)
        
        await db.commit()
        await db.refresh(portfolio)
        
        logger.info(f"User {user_id} sold {shares} shares of {symbol} at ${price:.2f} (P/L: ${profit_loss:.2f})")
        
        return {
            'status': 'success',
            'action': 'SELL',
            'symbol': symbol,
            'shares': shares,
            'price': price,
            'total_revenue': revenue,
            'profit_loss': profit_loss,
            'profit_loss_pct': profit_loss_pct,
            'remaining_cash': portfolio.cash
        }
    
    @staticmethod
    async def get_portfolio_summary(db: AsyncSession, user_id: int) -> Dict:
        portfolio = await UserPortfolioService.get_portfolio(db, user_id)
        
        if not portfolio:
            raise ValueError(f"Portfolio not found for user {user_id}")
        
        positions = portfolio.get_positions_dict()
        
        if not positions:
            return {
                'user_id': user_id,
                'cash': portfolio.cash,
                'total_value': portfolio.cash,
                'positions': [],
                'positions_count': 0,
                'invested_value': 0,
                'total_return': 0,
                'total_return_pct': 0
            }

        symbols = list(positions.keys())
        current_prices = await UserPortfolioService.get_current_prices(db, symbols)
        
        # Analyze positions
        position_list = []
        total_invested = 0
        total_current_value = 0
        
        for symbol, pos in positions.items():
            current_price = current_prices.get(symbol, pos['avg_price'])
            cost_basis = pos['shares'] * pos['avg_price']
            current_value = pos['shares'] * current_price
            profit_loss = current_value - cost_basis
            profit_loss_pct = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            buy_date = datetime.fromisoformat(pos['buy_date']) if isinstance(pos['buy_date'], str) else pos['buy_date']
            
            position_list.append({
                'symbol': symbol,
                'shares': pos['shares'],
                'avg_price': pos['avg_price'],
                'current_price': current_price,
                'cost_basis': cost_basis,
                'current_value': current_value,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'days_held': (datetime.now() - buy_date).days,
                'buy_date': pos['buy_date']
            })
            
            total_invested += cost_basis
            total_current_value += current_value
        
        total_value = portfolio.cash + total_current_value
        total_return = total_current_value - total_invested
        total_return_pct = (total_return / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'user_id': user_id,
            'cash': portfolio.cash,
            'total_value': total_value,
            'positions': position_list,
            'positions_count': len(position_list),
            'invested_value': total_invested,
            'current_positions_value': total_current_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'created_at': portfolio.created_at.isoformat(),
            'updated_at': portfolio.updated_at.isoformat()
        }
    
    @staticmethod
    async def get_transaction_history(db: AsyncSession, user_id: int, limit: int = 50) -> List[Dict]:
        portfolio = await UserPortfolioService.get_portfolio(db, user_id)
        
        if not portfolio:
            return []
        
        transactions = portfolio.get_transactions_list()
        
        # Return most recent first
        return list(reversed(transactions[-limit:]))

portfolio_service = UserPortfolioService()
