import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.market_agent import market_monitor
from app.agents.decision_agent import decision_maker
from app.agents.execution_agent import execution_agent

logger = logging.getLogger(__name__)


class TradingCoordinator:
    """
    1. Market Monitor analyzes stocks and makes predictions
    2. Decision Maker receives predictions and makes BUY/SELL/HOLD decisions
    3. Execution Agent executes decisions and tracks feedback
    4. Feedback loop improves future predictions
    """
    
    def __init__(self, user_id: Optional[int] = None, db_session: Optional[AsyncSession] = None):
        self.name = "Trading Coordinator"
        self.market_monitor = market_monitor
        self.decision_maker = decision_maker
        self.execution_agent = execution_agent
        
        if user_id and db_session:
            self.execution_agent.user_id = user_id
            self.execution_agent.db_session = db_session
        
        self.trading_sessions: List[Dict] = []
        self.is_running = False
        
        self._load_models_at_startup()
    
    def _load_models_at_startup(self):
        try:
            if self.market_monitor.load_model():
                logger.info(f"{self.name}: Market Monitor model loaded successfully")
            else:
                logger.info(f"{self.name}: No pre-trained Market Monitor model found")
            
            if self.decision_maker.load_model():
                logger.info(f"{self.name}: Decision Maker model loaded successfully")
            else:
                logger.info(f"{self.name}: No pre-trained Decision Maker model found")
        except Exception as e:
            logger.error(f"{self.name}: Error loading models at startup: {e}")
    
    async def run_trading_cycle(
        self,
        session: AsyncSession,
        symbols: List[str],
        use_csv: bool = False,
        risk_tolerance: Optional[float] = None
    ) -> Dict:
        if risk_tolerance is not None:
            self.decision_maker.set_risk_tolerance(risk_tolerance)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{self.name}: 🚀 Starting Trading Cycle")
        logger.info(f"{'='*60}")
        logger.info(f"Analyzing {len(symbols)} stocks: {', '.join(symbols)}")
        logger.info(f"Risk Tolerance: {self.decision_maker.risk_tolerance:.1%}")
        thresholds = self.decision_maker.get_thresholds()
        logger.info(f"Thresholds: BUY > {thresholds['buy_threshold_percent']:.2f}%, SELL < {thresholds['sell_threshold_percent']:.2f}%, Min Confidence: {thresholds['min_confidence']:.0%}")
        
        cycle_start = datetime.now()
        
        logger.info(f"\n{'-'*60}")
        logger.info("STEP 1: Market Analysis")
        logger.info(f"{'-'*60}")
        
        predictions = await self._market_analysis(session, symbols, use_csv)
        
        logger.info(f"\n{'-'*60}")
        logger.info("STEP 2: Decision Making")
        logger.info(f"{'-'*60}")
        
        decisions = self._make_decisions(predictions)
        
        logger.info(f"\n{'-'*60}")
        logger.info("STEP 3: Trade Execution")
        logger.info(f"{'-'*60}")
        
        execution_results = await self._execute_trades(session, decisions)
        
        logger.info(f"\n{'-'*60}")
        logger.info("STEP 4: Feedback Loop")
        logger.info(f"{'-'*60}")
        
        feedback_results = await self._check_feedback(session)
        
        cycle_end = datetime.now()
        cycle_duration = (cycle_end - cycle_start).total_seconds()
        
        summary = await self._generate_cycle_summary(
            predictions,
            decisions,
            execution_results,
            feedback_results,
            cycle_duration
        )
        
        trading_session = {
            "timestamp": cycle_start.isoformat(),
            "symbols": symbols,
            "predictions": predictions,
            "decisions": decisions,
            "executions": execution_results,
            "feedback": feedback_results,
            "summary": summary
        }
        
        self.trading_sessions.append(trading_session)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{self.name}: Trading Cycle Complete")
        logger.info(f"Duration: {cycle_duration:.1f}s")
        logger.info(f"{'='*60}\n")
        
        return trading_session
    
    async def _market_analysis(
        self,
        session: AsyncSession,
        symbols: List[str],
        use_csv: bool
    ) -> List[Dict]:
        predictions = []
        
        for symbol in symbols:
            try:
                if use_csv:
                    prediction = await self.market_monitor.predict_price_movement_from_csv(symbol)
                else:
                    prediction = await self.market_monitor.predict_price_movement(symbol, session)
                
                predictions.append(prediction)
                
            except Exception as e:
                logger.error(f"{self.name}: Error analyzing {symbol}: {e}")
                predictions.append({
                    "symbol": symbol,
                    "status": "error",
                    "error": str(e)
                })
        
        return predictions
    
    def _make_decisions(self, predictions: List[Dict]) -> List[Dict]:
        return self.decision_maker.analyze_portfolio(predictions)
    
    async def _execute_trades(
        self,
        session: AsyncSession,
        decisions: List[Dict]
    ) -> List[Dict]:
        execution_results = []
        
        for decision in decisions:
            try:
                symbol = decision.get("symbol")
                
                from app.models.stock import StockPrice
                from sqlalchemy import select
                
                query = select(StockPrice).where(
                    StockPrice.symbol == symbol
                ).order_by(StockPrice.date.desc()).limit(1)
                
                result = await session.execute(query)
                latest_record = result.scalar_one_or_none()
                
                if not latest_record:
                    execution_results.append({
                        "symbol": symbol,
                        "status": "failed",
                        "error": "No price data available"
                    })
                    continue
                
                current_price = float(latest_record.close)
                
                execution = await self.execution_agent.execute_decision(
                    decision,
                    current_price,
                    session
                )
                
                execution_results.append(execution)
                
            except Exception as e:
                logger.error(f"{self.name}: Error executing {decision.get('symbol')}: {e}")
                execution_results.append({
                    "symbol": decision.get("symbol"),
                    "status": "failed",
                    "error": str(e)
                })
        
        return execution_results
    
    async def _check_feedback(self, session: AsyncSession) -> List[Dict]:
        return await self.execution_agent.check_pending_feedback(
            session,
            self.market_monitor,
            self.decision_maker
        )
    
    async def _generate_cycle_summary(
        self,
        predictions: List[Dict],
        decisions: List[Dict],
        executions: List[Dict],
        feedback: List[Dict],
        duration: float
    ) -> Dict:
        buy_count = sum(1 for d in decisions if d.get("decision") == "BUY")
        sell_count = sum(1 for d in decisions if d.get("decision") == "SELL")
        hold_count = sum(1 for d in decisions if d.get("decision") == "HOLD")
        
        executed_trades = sum(
            1 for e in executions 
            if e.get("status") == "EXECUTED" and e.get("action_taken") in ["buy", "sell"]
        )
        
        portfolio = await self.execution_agent.get_portfolio_summary()
        performance = await self.execution_agent.get_performance_metrics()
        
        summary = {
            "duration_seconds": duration,
            "stocks_analyzed": len(predictions),
            "predictions_made": len([p for p in predictions if p.get("status") == "predicted"]),
            "decisions": {
                "buy": buy_count,
                "sell": sell_count,
                "hold": hold_count
            },
            "trades_executed": executed_trades,
            "feedback_items_processed": len(feedback),
            "portfolio": portfolio,
            "performance": performance
        }
        
        # Log summary
        logger.info(f"\n CYCLE SUMMARY:")
        logger.info(f"   Duration: {duration:.1f}s")
        logger.info(f"   Stocks Analyzed: {summary['stocks_analyzed']}")
        logger.info(f"   Decisions: BUY={buy_count}, SELL={sell_count}, HOLD={hold_count}")
        logger.info(f"   Trades Executed: {executed_trades}")
        logger.info(f"   Portfolio Value: ${portfolio['total_value']:.2f}")
        logger.info(f"   P&L: ${portfolio['profit_loss']:+.2f} ({portfolio['profit_loss_percent']:+.2f}%)")
        logger.info(f"   Win Rate: {performance['win_rate']:.1f}%")
        
        return summary
    
    async def train_all_agents(
        self,
        session: AsyncSession,
        symbols: Optional[List[str]] = None,
        use_sample: bool = False
    ) -> Dict:
        from pathlib import Path
        
        if symbols is None or len(symbols) == 0:
            dataset_dir = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
            
            if dataset_dir.exists():
                all_symbols = [f.stem for f in dataset_dir.glob("*.csv")]
                
                if use_sample:
                    symbols = all_symbols[:200]  # First 200 for sample
                    logger.info(f"Training on SAMPLE: {len(symbols)} stocks")
                else:
                    symbols = all_symbols
                    logger.info(f"Training on FULL DATASET: {len(symbols)} stocks")
            else:
                logger.error(f"Dataset directory not found: {dataset_dir}")
                return {
                    "status": "error",
                    "error": "Dataset directory not found"
                }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{self.name}: Training All Agents")
        logger.info(f"Symbols to process: {len(symbols)}")
        logger.info(f"{'='*60}")
        
        results = {}
        
        logger.info("\nTraining Market Monitor...")
        market_result = await self.market_monitor.train_model(symbols)
        results["market_monitor"] = market_result
        
        # train decision maker (if enough feedback available)
        logger.info("\nTraining Decision Maker...")
        decision_result = await self.decision_maker.train_from_feedback()
        results["decision_maker"] = decision_result
        
        logger.info(f"\n{'='*60}")
        logger.info(f"{self.name}: Training Complete")
        logger.info(f"{'='*60}\n")
        
        return results
    
    async def get_system_status(self) -> Dict:
        portfolio_info = {}
        if self.execution_agent.user_id and self.execution_agent.db_session:
            try:
                portfolio = await self.execution_agent.get_portfolio_summary()
                portfolio_info = {
                    "cash": portfolio["cash"],
                    "positions_count": portfolio["positions_count"],
                    "total_value": portfolio["total_value"]
                }
            except Exception as e:
                logger.error(f"Error getting portfolio for status: {e}")
                portfolio_info = {
                    "cash": 0,
                    "positions_count": 0,
                    "total_value": 0
                }
        else:
            portfolio_info = {
                "cash": 0,
                "positions_count": 0,
                "total_value": 0
            }
        
        return {
            "is_running": self.is_running,
            "total_trading_sessions": len(self.trading_sessions),
            "market_monitor": {
                "is_trained": self.market_monitor.is_trained,
                "model_exists": self.market_monitor.price_model is not None
            },
            "decision_maker": {
                "is_trained": self.decision_maker.is_trained,
                "risk_tolerance": self.decision_maker.risk_tolerance,
                "decision_history_size": len(self.decision_maker.decision_history),
                "feedback_data_size": len(self.decision_maker.feedback_data)
            },
            "execution_agent": {
                "capital": portfolio_info.get("cash", 0),
                **portfolio_info,
                "total_trades": self.execution_agent.total_trades,
                "winning_trades": self.execution_agent.winning_trades,
                "losing_trades": self.execution_agent.losing_trades,
                "win_rate": (
                    (self.execution_agent.winning_trades / max(self.execution_agent.total_trades, 1)) * 100
                )
            }
        }


trading_coordinator = TradingCoordinator()
