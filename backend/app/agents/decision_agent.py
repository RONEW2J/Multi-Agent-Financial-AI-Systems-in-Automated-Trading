import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


class Decision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class DecisionMakingAgent:
    """
    - Receives predictions from Market Monitor
    - Uses ML model to make trading decisions
    - Learns from execution feedback
    """
    
    def __init__(self, risk_tolerance: float = 0.5):
        self.name = "Decision Maker AI"
        self.risk_tolerance = risk_tolerance  # 0.0 (conservative) to 1.0 (aggressive)
        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.decision_model: Optional[GradientBoostingClassifier] = None
        self.scaler = StandardScaler()
        self.is_trained = False
        
        self.decision_history: List[Dict] = []
        self.feedback_data: List[Dict] = []
    
    def set_risk_tolerance(self, risk_tolerance: float):
        self.risk_tolerance = max(0.0, min(1.0, risk_tolerance))
        logger.info(f"{self.name}: Risk tolerance set to {self.risk_tolerance:.2f}")
    
    def get_thresholds(self) -> Dict:
        buy_threshold = 1.0 - (self.risk_tolerance * 0.9)
        sell_threshold = -1.0 + (self.risk_tolerance * 0.9)
        min_confidence = 0.6 - (self.risk_tolerance * 0.2)
        return {
            "risk_tolerance": self.risk_tolerance,
            "buy_threshold_percent": buy_threshold,
            "sell_threshold_percent": sell_threshold,
            "min_confidence": min_confidence
        }
    
    def extract_decision_features(self, prediction: Dict) -> np.ndarray:
        """
        features from market prediction for decision making
        """
        if prediction.get("status") != "predicted":
            return np.array([])
        
        features = [
            prediction.get("predicted_change_percent", 0),
            prediction.get("confidence", 0),
            prediction.get("current_price", 0),
            prediction.get("technical_indicators", {}).get("RSI", 50),
            prediction.get("technical_indicators", {}).get("MACD", 0),
            prediction.get("technical_indicators", {}).get("BB_Position", 0.5),
            prediction.get("technical_indicators", {}).get("Distance_MA20", 0),
            self.risk_tolerance
        ]
        
        return np.array(features).reshape(1, -1)
    
    def make_rule_based_decision(self, prediction: Dict) -> Dict:
        """
        make decision using rule-based logic (fallback when model not trained)
        """
        symbol = prediction.get("symbol", "UNKNOWN")
        
        if prediction.get("status") != "predicted":
            return {
                "symbol": symbol,
                "decision": Decision.HOLD,
                "confidence": 0.0,
                "reason": "No prediction available",
                "method": "rule_based"
            }
        
        predicted_change = prediction.get("predicted_change_percent", 0)
        pred_confidence = prediction.get("confidence", 0)
        rsi = prediction.get("technical_indicators", {}).get("RSI", 50)
        
        # decision logic based on prediction and risk tolerance
        decision = Decision.HOLD
        confidence = 0.5
        reasons = []
        
        # thresholds based on risk tolerance (more aggressive with higher risk)
        # Conservative (0.0): BUY > 1.0%, SELL < -1.0%, confidence >= 0.6
        # Moderate (0.5): BUY > 0.5%, SELL < -0.5%, confidence >= 0.5
        # Aggressive (1.0): BUY > 0.1%, SELL < -0.1%, confidence >= 0.4
        buy_threshold = 1.0 - (self.risk_tolerance * 0.9)  # 1.0% to 0.1%
        sell_threshold = -1.0 + (self.risk_tolerance * 0.9)  # -1.0% to -0.1%
        min_confidence = 0.6 - (self.risk_tolerance * 0.2)  # 0.6 to 0.4
        
        # BUY signal
        if predicted_change > buy_threshold and pred_confidence >= min_confidence:
            if rsi < 70:  # Not overbought
                decision = Decision.BUY
                confidence = pred_confidence
                reasons.append(f"ML predicts +{predicted_change:.2f}% gain")
                reasons.append(f"RSI at {rsi:.0f} (not overbought)")
            else:
                reasons.append("Overbought condition (RSI > 70)")
        
        # SELL signal
        elif predicted_change < sell_threshold and pred_confidence >= min_confidence:
            if rsi > 30:  # Not oversold
                decision = Decision.SELL
                confidence = pred_confidence
                reasons.append(f"ML predicts {predicted_change:.2f}% loss")
                reasons.append(f"RSI at {rsi:.0f} (not oversold)")
            else:
                reasons.append("Oversold condition (RSI < 30)")
        
        # HOLD
        else:
            reasons.append("Prediction below threshold or low confidence")
            reasons.append(f"Predicted change: {predicted_change:+.2f}%")
        
        return {
            "symbol": symbol,
            "decision": decision.value,
            "confidence": float(confidence),
            "reasons": reasons,
            "predicted_change": float(predicted_change),
            "pred_confidence": float(pred_confidence),
            "method": "rule_based",
            "timestamp": datetime.now().isoformat()
        }
    
    def make_ml_decision(self, prediction: Dict) -> Dict:
        features = self.extract_decision_features(prediction)
        
        if len(features) == 0:
            return self.make_rule_based_decision(prediction)
        
        features_scaled = self.scaler.transform(features)
        
        # predict decision class (0=SELL, 1=HOLD, 2=BUY)
        decision_class = self.decision_model.predict(features_scaled)[0]
        decision_proba = self.decision_model.predict_proba(features_scaled)[0]
        
        decision_map = {0: Decision.SELL, 1: Decision.HOLD, 2: Decision.BUY}
        decision = decision_map[decision_class]
        confidence = float(decision_proba[decision_class])
        
        return {
            "symbol": prediction.get("symbol"),
            "decision": decision.value,
            "confidence": confidence,
            "predicted_change": prediction.get("predicted_change_percent"),
            "reasons": [f"ML model decision with {confidence:.0%} confidence"],
            "method": "ml_model",
            "timestamp": datetime.now().isoformat()
        }
    
    def make_decision(self, prediction: Dict) -> Dict:
        symbol = prediction.get("symbol", "UNKNOWN")
        logger.info(f"{self.name}: Making decision for {symbol}...")
        
        if self.is_trained and self.decision_model is not None:
            decision = self.make_ml_decision(prediction)
        else:
            decision = self.make_rule_based_decision(prediction)
        
        # Store in history
        self.decision_history.append(decision)
        
        logger.info(
            f"{self.name}: {symbol} -> {decision['decision']} "
            f"(Confidence: {decision['confidence']:.0%}, Method: {decision.get('method', 'unknown')})"
        )
        
        return decision
    
    def analyze_portfolio(self, predictions: List[Dict]) -> List[Dict]:
        logger.info(f"{self.name}: Analyzing {len(predictions)} predictions...")
        
        decisions = []
        for prediction in predictions:
            try:
                decision = self.make_decision(prediction)
                decisions.append(decision)
            except Exception as e:
                logger.error(f"{self.name}: Error processing {prediction.get('symbol')}: {e}")
                decisions.append({
                    "symbol": prediction.get("symbol", "UNKNOWN"),
                    "decision": Decision.HOLD,
                    "confidence": 0.0,
                    "reason": f"Error: {str(e)}"
                })

        buy_count = sum(1 for d in decisions if d["decision"] == "BUY")
        sell_count = sum(1 for d in decisions if d["decision"] == "SELL")
        hold_count = sum(1 for d in decisions if d["decision"] == "HOLD")
        
        logger.info(
            f"{self.name}: Decisions - BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}"
        )
        
        return decisions
    
    def add_feedback(self, decision: Dict, execution_result: Dict, actual_outcome: Dict):
        """
        record feedback from execution for future learning
        
        Args:
            decision: Original decision made
            execution_result: Result from execution agent
            actual_outcome: Actual price change after N days
        """
        feedback = {
            "symbol": decision.get("symbol"),
            "decision": decision.get("decision"),
            "confidence": decision.get("confidence"),
            "predicted_change": decision.get("predicted_change"),
            "actual_change": actual_outcome.get("actual_change_percent"),
            "profit_loss": execution_result.get("profit_loss", 0),
            "was_correct": self._was_decision_correct(decision, actual_outcome),
            "timestamp": datetime.now().isoformat()
        }
        
        self.feedback_data.append(feedback)
        logger.info(
            f"{self.name}: Feedback recorded for {feedback['symbol']} - "
            f"Correct: {feedback['was_correct']}"
        )
    
    def _was_decision_correct(self, decision: Dict, actual_outcome: Dict) -> bool:
        decision_type = decision.get("decision")
        actual_change = actual_outcome.get("actual_change_percent", 0)
        
        if decision_type == "BUY":
            return actual_change > 0  # profitable if price went up
        elif decision_type == "SELL":
            return actual_change < 0  # correct if we avoided loss
        else:  # HOLD
            return abs(actual_change) < 2  # correct if not much happened
    
    async def train_from_feedback(self) -> Dict:
        if len(self.feedback_data) < 50:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 50 feedback samples, have {len(self.feedback_data)}"
            }
        
        logger.info(f"{self.name}: Training decision model from {len(self.feedback_data)} feedback samples...")
        
        X = []
        y = []
        
        for feedback in self.feedback_data:
            features = [
                feedback.get("predicted_change", 0),
                feedback.get("confidence", 0),
                # Add more features from the original decision context
            ]
            
            actual_change = feedback.get("actual_change", 0)
            if actual_change > 2:
                label = 2  # should have been BUY
            elif actual_change < -2:
                label = 0  # should have been SELL
            else:
                label = 1  # should have been HOLD
            
            X.append(features)
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        self.decision_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        
        self.decision_model.fit(X_scaled, y)
        self.is_trained = True
        
        accuracy = self.decision_model.score(X_scaled, y)
        
        self.save_model()
        
        logger.info(f"{self.name}: Decision model trained! Accuracy: {accuracy:.2%}")
        
        return {
            "status": "success",
            "accuracy": float(accuracy),
            "samples_used": len(X),
            "timestamp": datetime.now().isoformat()
        }
    
    def save_model(self):
        if self.decision_model is None:
            return
        
        model_path = self.models_dir / "decision_model.joblib"
        scaler_path = self.models_dir / "decision_scaler.joblib"
        
        joblib.dump(self.decision_model, model_path)
        joblib.dump(self.scaler, scaler_path)
        
        logger.info(f"{self.name}: Model saved")
    
    def load_model(self) -> bool:
        try:
            model_path = self.models_dir / "decision_model.joblib"
            scaler_path = self.models_dir / "decision_scaler.joblib"
            
            if not model_path.exists():
                return False
            
            self.decision_model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.is_trained = True
            
            logger.info(f"{self.name}: Model loaded")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Error loading model: {e}")
            return False


decision_maker = DecisionMakingAgent(risk_tolerance=0.5)
