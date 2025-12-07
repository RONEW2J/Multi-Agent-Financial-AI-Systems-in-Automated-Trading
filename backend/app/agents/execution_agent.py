import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.stock import StockPrice
from app.services.portfolio_service import portfolio_service

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionAgent:
    """
    - Executes trading decisions
    - Uses user portfolio service for actual trading
    - Provides feedback loop for model improvement
    - Calculates prediction accuracy
    """
    
    def __init__(self, user_id: Optional[int] = None, db_session: Optional[AsyncSession] = None):
        self.name = "Execution Agent"
        self.user_id = user_id
        self.db_session = db_session
        
        # Tracking
        self.executed_orders: List[Dict] = []
        self.pending_feedback: List[Dict] = []
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit_loss = 0.0
    
    async def load_trade_stats(self) -> None:
        if not self.user_id or not self.db_session:
            return
        
        try:
            from app.services.portfolio_service import portfolio_service
            
            transactions = await portfolio_service.get_transaction_history(
                self.db_session, self.user_id, limit=1000
            )
            
            buy_count = sum(1 for t in transactions if t.get('type') == 'BUY')
            sell_count = sum(1 for t in transactions if t.get('type') == 'SELL')
            
            self.total_trades = buy_count + sell_count
            
            # calculate winning/losing trades from SELL transactions
            for tx in transactions:
                if tx.get('type') == 'SELL':
                    profit = tx.get('profit_loss', 0)
                    if profit > 0:
                        self.winning_trades += 1
                    elif profit < 0:
                        self.losing_trades += 1
                    self.total_profit_loss += profit
            
            logger.info(
                f"{self.name}: Loaded stats - {self.total_trades} trades, "
                f"{self.winning_trades}W/{self.losing_trades}L"
            )
        except Exception as e:
            logger.error(f"{self.name}: Error loading trade stats: {e}")
    
    async def get_portfolio_summary(self) -> Dict:
        if not self.user_id or not self.db_session:
            return {
                "cash": 0,
                "positions_value": 0,
                "total_value": 0,
                "profit_loss": 0,
                "profit_loss_percent": 0,
                "positions_count": 0,
                "positions": []
            }
        
        try:
            summary = await portfolio_service.get_portfolio_summary(self.db_session, self.user_id)
            return {
                "cash": summary["cash"],
                "positions_value": summary["current_positions_value"],
                "total_value": summary["total_value"],
                "profit_loss": summary["total_return"],
                "profit_loss_percent": summary["total_return_pct"],
                "positions_count": summary["positions_count"],
                "positions": summary["positions"]
            }
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                "cash": 0,
                "positions_value": 0,
                "total_value": 0,
                "profit_loss": 0,
                "profit_loss_percent": 0,
                "positions_count": 0,
                "positions": []
            }
    
    async def execute_decision(
        self,
        decision: Dict,
        current_price: float,
        session: Optional[AsyncSession] = None
    ) -> Dict:
        symbol = decision.get("symbol")
        action = decision.get("decision")
        confidence = decision.get("confidence", 0)
        
        logger.info(
            f"{self.name}: Executing {action} for {symbol} @ ${current_price:.2f} "
            f"(Confidence: {confidence:.0%})"
        )
        
        # based on confidence and risk management
        position_size = await self._calculate_position_size(confidence, current_price)
        
        result = {
            "symbol": symbol,
            "action": action,
            "price": current_price,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "status": OrderStatus.EXECUTED,
        }
        
        try:
            if action == "BUY":
                result.update(await self._execute_buy(symbol, current_price, position_size))
            elif action == "SELL":
                result.update(await self._execute_sell(symbol, current_price))
            else:  # HOLD
                result.update({
                    "action_taken": "none",
                    "reason": "HOLD decision - no trade executed"
                })
            
            self.executed_orders.append(result)
            
            if action in ["BUY", "SELL"]:
                self._schedule_feedback_tracking(decision, result)
            
        except Exception as e:
            logger.error(f"{self.name}: Execution failed for {symbol}: {e}")
            result["status"] = OrderStatus.FAILED
            result["error"] = str(e)
        
        return result
    
    async def _calculate_position_size(self, confidence: float, price: float) -> int:
        """
        Risk management rules:
        - Never risk more than 10% of capital on single trade
        - Scale position size with confidence (50% to 100% of max)
        - Minimum position: $1000 worth
        """
        if not self.user_id or not self.db_session:
            return 1
        
        try:
            portfolio = await self.get_portfolio_summary()
            capital = portfolio["cash"]
            
            max_risk_per_trade = capital * 0.10
            confidence_factor = 0.5 + (confidence * 0.5)
            
            position_value = max_risk_per_trade * confidence_factor
            position_value = max(position_value, 1000)  
            
            shares = int(position_value / price)
            return max(shares, 1)  
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 1
    
    async def _execute_buy(self, symbol: str, price: float, quantity: int) -> Dict:
        if not self.user_id or not self.db_session:
            return {
                "action_taken": "rejected",
                "reason": "No user portfolio configured",
                "status": OrderStatus.FAILED
            }
        
        try:
            result = await portfolio_service.buy_stock(
                self.db_session,
                self.user_id,
                symbol,
                quantity,
                price
            )
            
            self.total_trades += 1
            total_cost = result.get("total_cost", quantity * price)
            
            logger.info(
                f"{self.name}: BOUGHT {quantity} shares of {symbol} @ ${price:.2f} "
                f"(Total: ${total_cost:.2f})"
            )
            
            return {
                "action_taken": "buy",
                "shares": quantity,
                "total": total_cost,
                "remaining_capital": result.get("remaining_cash", 0),
                "status": OrderStatus.EXECUTED
            }
        except ValueError as e:
            logger.error(f"{self.name}: Buy failed for {symbol}: {e}")
            return {
                "action_taken": "rejected",
                "reason": str(e),
                "status": OrderStatus.FAILED
            }
    
    async def _execute_sell(self, symbol: str, price: float) -> Dict:
        if not self.user_id or not self.db_session:
            return {
                "action_taken": "rejected",
                "reason": "No user portfolio configured",
                "status": OrderStatus.FAILED
            }
        
        try:
            portfolio = await self.get_portfolio_summary()
            position = None
            for pos in portfolio["positions"]:
                if pos["symbol"] == symbol:
                    position = pos
                    break
            
            if not position:
                return {
                    "action_taken": "rejected",
                    "reason": f"No position in {symbol} to sell",
                    "status": OrderStatus.FAILED
                }
            
            quantity = position["shares"]
            avg_price = position["avg_price"]
            
            result = await portfolio_service.sell_stock(
                self.db_session,
                self.user_id,
                symbol,
                quantity,
                price
            )
            
            proceeds = result.get("total_revenue", quantity * price)
            profit_loss = result.get("profit_loss", proceeds - (avg_price * quantity))
            profit_loss_percent = result.get("profit_loss_pct", (profit_loss / (avg_price * quantity)) * 100 if avg_price * quantity > 0 else 0)
            
            # update metrics
            self.total_trades += 1
            self.total_profit_loss += profit_loss
            if profit_loss > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            logger.info(
                f"{self.name}: SOLD {quantity} shares of {symbol} @ ${price:.2f} "
                f"(P&L: ${profit_loss:+.2f} / {profit_loss_percent:+.2f}%)"
            )
            
            return {
                "action_taken": "sell",
                "shares": quantity,
                "avg_entry_price": avg_price,
                "exit_price": price,
                "total": proceeds,
                "profit_loss": profit_loss,
                "profit_loss_percent": profit_loss_percent,
                "remaining_capital": result.get("remaining_cash", 0),
                "status": OrderStatus.EXECUTED
            }
        except ValueError as e:
            logger.error(f"{self.name}: Sell failed for {symbol}: {e}")
            return {
                "action_taken": "rejected",
                "reason": str(e),
                "status": OrderStatus.FAILED
            }
    
    def _schedule_feedback_tracking(self, decision: Dict, execution_result: Dict):
        """
        will be checked after 1 day to compare predicted vs actual
        """
        tracking = {
            "symbol": decision.get("symbol"),
            "decision": decision,
            "execution": execution_result,
            "execution_date": datetime.now(),
            "check_date": datetime.now() + timedelta(days=1),
            "checked": False
        }
        
        self.pending_feedback.append(tracking)
        logger.info(
            f"{self.name}: Scheduled feedback check for {tracking['symbol']} "
            f"on {tracking['check_date'].date()}"
        )
    
    async def check_pending_feedback(
        self,
        session: AsyncSession,
        market_agent,
        decision_agent
    ) -> List[Dict]:
        feedback_results = []
        now = datetime.now()
        
        for tracking in self.pending_feedback:
            if tracking["checked"]:
                continue
            
            if now < tracking["check_date"]:
                continue  # not time yet
            
            symbol = tracking["symbol"]
            logger.info(f"{self.name}: Checking feedback for {symbol}...")
            
            try:
                actual_outcome = await self._get_actual_outcome(
                    session,
                    symbol,
                    tracking["execution_date"],
                    tracking["check_date"]
                )
                
                # calculate if prediction was accurate
                predicted_change = tracking["decision"].get("predicted_change", 0)
                actual_change = actual_outcome.get("actual_change_percent", 0)
                
                prediction_error = abs(predicted_change - actual_change)
                is_accurate = prediction_error < 3.0  # within 3% tolerance
                
                feedback = {
                    "symbol": symbol,
                    "predicted_change": predicted_change,
                    "actual_change": actual_change,
                    "prediction_error": prediction_error,
                    "is_accurate": is_accurate,
                    "execution_result": tracking["execution"],
                    "timestamp": now.isoformat()
                }
                
                decision_agent.add_feedback(
                    tracking["decision"],
                    tracking["execution"],
                    actual_outcome
                )
                
                feedback_results.append(feedback)
                tracking["checked"] = True
                
                logger.info(
                    f"{self.name}: Feedback for {symbol} - "
                    f"Predicted: {predicted_change:+.2f}%, Actual: {actual_change:+.2f}%, "
                    f"Error: {prediction_error:.2f}%, Accurate: {is_accurate}"
                )
                
            except Exception as e:
                logger.error(f"{self.name}: Error checking feedback for {symbol}: {e}")
        
        return feedback_results
    
    async def _get_actual_outcome(
        self,
        session: AsyncSession,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        start_date_str = start_date.strftime('%Y-%m-%d')
        start_query = select(StockPrice).where(
            StockPrice.symbol == symbol,
            StockPrice.date >= start_date_str,
        ).order_by(StockPrice.date.asc()).limit(1)
        
        start_result = await session.execute(start_query)
        start_record = start_result.scalar_one_or_none()
        
        end_date_str = end_date.strftime('%Y-%m-%d')
        end_query = select(StockPrice).where(
            StockPrice.symbol == symbol,
            StockPrice.date >= end_date_str,
        ).order_by(StockPrice.date.asc()).limit(1)
        
        end_result = await session.execute(end_query)
        end_record = end_result.scalar_one_or_none()
        
        if not start_record or not end_record:
            raise ValueError(f"Could not find price data for {symbol}")
        
        start_price = start_record.close
        end_price = end_record.close
        change_percent = ((end_price - start_price) / start_price) * 100
        
        return {
            "symbol": symbol,
            "start_price": float(start_price),
            "end_price": float(end_price),
            "actual_change_percent": float(change_percent),
            "start_date": start_record.date,
            "end_date": end_record.date
        }
    
    async def get_performance_metrics(self) -> Dict:
        """Get detailed performance metrics"""
        total_trades = max(self.total_trades, 1)  # avoid division by zero
        win_rate = (self.winning_trades / total_trades) * 100
        
        portfolio = await self.get_portfolio_summary()
        
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "total_profit_loss": self.total_profit_loss,
            "portfolio": portfolio,
            "pending_feedback_count": len([f for f in self.pending_feedback if not f["checked"]]),
            "completed_feedback_count": len([f for f in self.pending_feedback if f["checked"]])
        }


execution_agent = ExecutionAgent()
