import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import os

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock import StockPrice
from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


class MarketMonitoringAgent:
    """
    - Loads historical data from CSV dataset
    - Trains ML models to recognize patterns
    - Predicts future price movements
    """
    
    def __init__(self):
        self.name = "Market Monitor AI"
        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.price_model: Optional[RandomForestRegressor] = None
        self.scaler = MinMaxScaler()
        self.feature_columns = []
        self.is_trained = False
        
        # Historical pattern database
        self.pattern_database: Dict[str, List[Dict]] = {}
        
    async def load_historical_data_from_csv(self, symbol: str, csv_path: str) -> pd.DataFrame:
        """Load historical data from CSV file"""
        try:
            df = pd.read_csv(csv_path)
            
            if 'ticker' in df.columns and 'date' in df.columns:
                df = df.rename(columns={
                    'ticker': 'Symbol',
                    'date': 'Date',
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close'
                })
                if 'Volume' not in df.columns:
                    df['Volume'] = 1000000  # default volume for stocks without volume data
            
            required_cols = ['Date', 'Open', 'High', 'Low', 'Close']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"CSV missing required columns. Has: {df.columns.tolist()}")
                return pd.DataFrame()
            
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            if 'Symbol' not in df.columns:
                df['Symbol'] = symbol
            
            logger.info(f"{self.name}: Loaded {len(df)} records for {symbol} from CSV")
            return df
            
        except Exception as e:
            logger.error(f"{self.name}: Error loading CSV for {symbol}: {e}")
            return pd.DataFrame()
    
    async def load_historical_data_from_db(self, symbol: str, db: AsyncSession) -> pd.DataFrame:
        query = select(StockPrice).where(
            StockPrice.symbol == symbol
        ).order_by(StockPrice.date)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        if not records:
            return pd.DataFrame()
        
        data = [{
            'Date': record.date,
            'Open': record.open,
            'High': record.high,
            'Low': record.low,
            'Close': record.close,
            'Volume': record.volume,
            'Symbol': record.symbol
        } for record in records]
        
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        - Moving averages (MA5, MA10, MA20)
        - Relative Strength Index (RSI)
        - MACD
        - Bollinger Bands
        - Price momentum
        - Volume changes
        - RELATIVE features (not dependent on absolute price)
        """
        if len(df) < 20:
            return df
        
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # Price changes (RELATIVE - as percentage)
        df['Price_Change'] = df['Close'].pct_change(fill_method=None)
        df['Price_Range'] = (df['High'] - df['Low']) / df['Low']
        
        # Volume changes
        df['Volume_Change'] = df['Volume'].pct_change(fill_method=None)
        df['Volume_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # RSI (Relative Strength Index) - already 0-100 scale
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD - normalize by price to make it relative
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = (exp1 - exp2) / df['Close'] * 100  # as % of price
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])
        
        # Momentum indicators (absolute - used internally)
        df['Momentum_5'] = df['Close'] - df['Close'].shift(5)
        df['Momentum_10'] = df['Close'] - df['Close'].shift(10)
        
        # Price distance from MA (RELATIVE)
        df['Distance_MA5'] = (df['Close'] - df['MA5']) / df['MA5']
        df['Distance_MA20'] = (df['Close'] - df['MA20']) / df['MA20']
        
        # Additional RELATIVE features for model training and prediction
        df['Open_Close_Ratio'] = (df['Open'] - df['Close']) / df['Close'] * 100
        df['High_Low_Ratio'] = (df['High'] - df['Low']) / df['Low'] * 100
        df['Close_MA5_Ratio'] = (df['Close'] - df['MA5']) / df['MA5'] * 100
        df['Close_MA10_Ratio'] = (df['Close'] - df['MA10']) / df['MA10'] * 100
        df['Close_MA20_Ratio'] = (df['Close'] - df['MA20']) / df['MA20'] * 100
        df['MA5_MA20_Cross'] = (df['MA5'] - df['MA20']) / df['MA20'] * 100
        df['Momentum_5_Pct'] = df['Momentum_5'] / df['Close'].shift(5) * 100
        df['Momentum_10_Pct'] = df['Momentum_10'] / df['Close'].shift(10) * 100
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA5']
        
        return df
    
    def prepare_training_data(self, df: pd.DataFrame, prediction_days: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Target: predict price change % in next N days
        Using only RELATIVE/NORMALIZED features, not absolute prices
        This ensures the model works across stocks with different price ranges ($1 to $5000+)
        """
        # Make a copy to avoid SettingWithCopyWarning
        df = df.copy()
        df = self.calculate_technical_indicators(df)
        
        # Drop NaN values from indicator calculations
        df = df.dropna()
        
        if len(df) < 30:
            return np.array([]), np.array([])
        
        # Feature columns - ONLY relative/normalized features!
        # NO absolute prices (Open, High, Low, Close, MA5, MA10, MA20, Volume)
        self.feature_columns = [
            # Price change features (already %)
            'Price_Change',      # Daily % change
            'Price_Range',       # Daily high-low % range
            
            # Relative position features
            'Open_Close_Ratio',  # Open vs Close %
            'High_Low_Ratio',    # High vs Low %
            'Close_MA5_Ratio',   # Distance from MA5 %
            'Close_MA10_Ratio',  # Distance from MA10 %
            'Close_MA20_Ratio',  # Distance from MA20 %
            'Distance_MA5',      # Already %
            'Distance_MA20',     # Already %
            'MA5_MA20_Cross',    # MA crossover signal %
            
            # Momentum features (as %)
            'Momentum_5_Pct',    # 5-day momentum %
            'Momentum_10_Pct',   # 10-day momentum %
            
            # Technical indicators (already normalized 0-100 or relative)
            'RSI',               # 0-100 scale
            'BB_Position',       # 0-1 scale (position in Bollinger Bands)
            'MACD',              # Relative to price movement (%)
            'MACD_Signal',       # Relative to price movement (%)
            
            # Volume features (normalized)
            'Volume_Change',     # % change in volume
            'Volume_Ratio',      # Relative to 5-day average
        ]
        
        # Calculate target: price change in next N days
        df['Target'] = df['Close'].shift(-prediction_days) / df['Close'] - 1
        df['Target'] = df['Target'] * 100  # convert to percentage
        
        # Remove last rows without target
        df = df[:-prediction_days]
        df = df.dropna()
        
        # Replace infinity and NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna()
        
        # Clipping outliers in target to prevent extreme values from dominating
        # Most 5-day stock movements are within ±30%, anything beyond is likely an outlier
        # (stock splits, extreme events, data errors, penny stocks)
        target_clip = 30.0  # ±30% max
        outliers_count = ((df['Target'] > target_clip) | (df['Target'] < -target_clip)).sum()
        if outliers_count > 0:
            logger.debug(f"Clipping {outliers_count} outlier targets (>{target_clip}% or <-{target_clip}%)")
        df['Target'] = df['Target'].clip(-target_clip, target_clip)
        
        # Also clipping extreme feature values to prevent model from overfitting to outliers
        for col in self.feature_columns:
            if col in df.columns:
                # Clip features at 99.5th percentile (both tails)
                lower = df[col].quantile(0.005)
                upper = df[col].quantile(0.995)
                df[col] = df[col].clip(lower, upper)
        
        if len(df) < 30:
            return np.array([]), np.array([])
        
        X = df[self.feature_columns].values
        y = df['Target'].values
        
        return X, y
    
    async def train_model(self, symbols: List[str], dataset_path: str = None) -> Dict:
        if dataset_path is None:
            dataset_path = Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks"
        
        logger.info(f"\n{'='*80}")
        logger.info(f"{self.name}: 🎓 STARTING MODEL TRAINING")
        logger.info(f"{'='*80}")
        logger.info(f" Total stocks to process: {len(symbols)}")
        logger.info(f" Dataset path: {dataset_path}")
        logger.info(f"{'='*80}\n")
        
        all_X = []
        all_y = []
        training_stats = {
            "stocks_processed": 0,
            "total_samples": 0,
            "stocks_failed": []
        }
        
        for idx, symbol in enumerate(symbols, 1):
            try:
                progress = (idx / len(symbols)) * 100
                logger.info(f"[{idx}/{len(symbols)}] ({progress:.1f}%) Processing {symbol}...")
                
                csv_file = Path(dataset_path) / f"{symbol}.csv"
                
                if csv_file.exists():
                    df = await self.load_historical_data_from_csv(symbol, str(csv_file))
                else:
                    logger.debug(f"  ↳ CSV not found, trying database...")
                    async with async_session_maker() as db:
                        df = await self.load_historical_data_from_db(symbol, db)
                
                if df.empty:
                    logger.warning(f"  ↳ ⚠️  No data for {symbol}, skipping")
                    training_stats["stocks_failed"].append(symbol)
                    continue
                
                X, y = self.prepare_training_data(df, prediction_days=5)
                
                if len(X) > 0:
                    all_X.append(X)
                    all_y.append(y)
                    training_stats["stocks_processed"] += 1
                    training_stats["total_samples"] += len(X)
                    logger.info(f"  ↳ {len(X):,} samples prepared (Total: {training_stats['total_samples']:,})")
                
            except Exception as e:
                logger.error(f"  ↳ ❌ Error processing {symbol}: {e}")
                training_stats["stocks_failed"].append(symbol)
        
        logger.info(f"\n{'-'*80}")
        logger.info(f" DATA PREPARATION COMPLETE")
        logger.info(f" Stocks processed: {training_stats['stocks_processed']}/{len(symbols)}")
        logger.info(f" Stocks failed: {len(training_stats['stocks_failed'])}")
        logger.info(f" Total samples: {training_stats['total_samples']:,}")
        logger.info(f"{'-'*80}\n")
        
        if not all_X:
            logger.error(f"{self.name}: ❌ No training data available!")
            return {"status": "failed", "error": "No training data"}
        
        # Combine all data
        logger.info(f" Combining data from all stocks...")
        X_combined = np.vstack(all_X)
        y_combined = np.concatenate(all_y)
        
        logger.info(f" Combined shape: X={X_combined.shape}, y={y_combined.shape}")
        
        # Scale features
        logger.info(f" Scaling features...")
        X_scaled = self.scaler.fit_transform(X_combined)
        logger.info(f" Scaling complete")
        
        # Train Random Forest model
        logger.info(f"\n{'-'*80}")
        logger.info(f" TRAINING RANDOM FOREST MODEL")
        logger.info(f" Estimators: 100")
        logger.info(f" Max depth: 15")
        logger.info(f" Training samples: {len(X_scaled):,}")
        logger.info(f"{'-'*80}")
        
        self.price_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1,
            verbose=1  # Show training progress
        )
        
        self.price_model.fit(X_scaled, y_combined)
        logger.info(f" Model training complete!")
        
        # Calculate training metrics
        logger.info(f"\n Calculating metrics...")
        y_pred = self.price_model.predict(X_scaled)
        mse = mean_squared_error(y_combined, y_pred)
        mae = mean_absolute_error(y_combined, y_pred)
        
        training_stats["mse"] = float(mse)
        training_stats["mae"] = float(mae)
        training_stats["rmse"] = float(np.sqrt(mse))
        
        logger.info(f" MSE:  {mse:.4f}")
        logger.info(f" MAE:  {mae:.4f}")
        logger.info(f" RMSE: {np.sqrt(mse):.4f}")
        
        # Feature importance
        logger.info(f"\n Top 10 Feature Importances:")
        feature_importance = dict(zip(
            self.feature_columns,
            self.price_model.feature_importances_
        ))
        training_stats["feature_importance"] = {
            k: float(v) for k, v in sorted(
                feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
        
        for i, (feature, importance) in enumerate(list(training_stats["feature_importance"].items()), 1):
            logger.info(f"  {i:2d}. {feature:20s}: {importance:.4f} ({importance*100:.2f}%)")
        
        self.is_trained = True

        logger.info(f"\n💾 Saving model...")
        self.save_model()
        
        logger.info(f"\n{'='*80}")
        logger.info(f" MODEL TRAINING COMPLETE!")
        logger.info(f" Stocks processed: {training_stats['stocks_processed']:,}")
        logger.info(f" Total samples: {training_stats['total_samples']:,}")
        logger.info(f" RMSE: {training_stats['rmse']:.4f}%")
        logger.info(f" MAE: {training_stats['mae']:.4f}%")
        logger.info(f"{'='*80}\n")
        
        return {
            "status": "success",
            "training_stats": training_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_model(self):
        if self.price_model is None:
            return
        
        model_path = self.models_dir / "market_monitor_model.joblib"
        scaler_path = self.models_dir / "market_monitor_scaler.joblib"
        
        joblib.dump(self.price_model, model_path)
        joblib.dump(self.scaler, scaler_path)
        joblib.dump(self.feature_columns, self.models_dir / "feature_columns.joblib")
        
        logger.info(f"{self.name}: Model saved to {model_path}")
    
    def load_model(self) -> bool:
        try:
            model_path = self.models_dir / "market_monitor_model.joblib"
            scaler_path = self.models_dir / "market_monitor_scaler.joblib"
            
            if not model_path.exists() or not scaler_path.exists():
                return False
            
            self.price_model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.feature_columns = joblib.load(self.models_dir / "feature_columns.joblib")
            self.is_trained = True
            
            logger.info(f"{self.name}: Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"{self.name}: Error loading model: {e}")
            return False
    
    async def predict_price_movement(self, symbol: str, db: AsyncSession) -> Dict:
        if not self.is_trained:
            return {
                "symbol": symbol,
                "status": "error",
                "message": "Model not trained yet"
            }
        
        df = await self.load_historical_data_from_db(symbol, db)
        
        if df.empty or len(df) < 30:
            return {
                "symbol": symbol,
                "status": "error",
                "message": "Insufficient data"
            }
        
        df = self.calculate_technical_indicators(df)
        df = df.dropna()
        
        if df.empty:
            return {
                "symbol": symbol,
                "status": "error",
                "message": "Error calculating indicators"
            }
        
        latest_features = df[self.feature_columns].iloc[-1:].values
        features_scaled = self.scaler.transform(latest_features)
        
        predicted_change = self.price_model.predict(features_scaled)[0]
        
        current_price = df['Close'].iloc[-1]
        predicted_price = current_price * (1 + predicted_change / 100)
        
        confidence = min(0.95, 0.5 + abs(predicted_change) / 20)
        
        if predicted_change > 1.0:
            direction = "UP"
        elif predicted_change < -1.0:
            direction = "DOWN"
        else:
            direction = "STABLE"
        
        return {
            "symbol": symbol,
            "status": "predicted",
            "current_price": float(current_price),
            "predicted_change_percent": float(predicted_change),
            "predicted_price": float(predicted_price),
            "direction": direction,
            "confidence": float(confidence),
            "technical_indicators": {
                "RSI": float(df['RSI'].iloc[-1]),
                "MACD": float(df['MACD'].iloc[-1]),
                "BB_Position": float(df['BB_Position'].iloc[-1]),
                "Distance_MA20": float(df['Distance_MA20'].iloc[-1])
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def predict_price_movement_from_csv(self, symbol: str, dataset_path: str = None) -> Dict:
        if not self.is_trained:
            return {
                "symbol": symbol,
                "status": "error",
                "message": "Model not trained yet"
            }
        
        if dataset_path is None:
            dataset_path = str(Path(__file__).parent.parent.parent / "dataset_of_stocks" / "stocks")

        csv_file = Path(dataset_path) / f"{symbol}.csv"
        
        if not csv_file.exists():
            return {
                "symbol": symbol,
                "status": "error",
                "message": f"CSV file not found: {csv_file}"
            }
        
        df = await self.load_historical_data_from_csv(symbol, str(csv_file))
        
        if df.empty or len(df) < 30:
            return {
                "symbol": symbol,
                "status": "error",
                "message": "Insufficient data"
            }
        
        df = self.calculate_technical_indicators(df)
        df = df.dropna()
        
        if df.empty:
            return {
                "symbol": symbol,
                "status": "error",
                "message": "Error calculating indicators"
            }

        latest_features = df[self.feature_columns].iloc[-1:].values
        features_scaled = self.scaler.transform(latest_features)

        predicted_change = self.price_model.predict(features_scaled)[0]
        
        current_price = df['Close'].iloc[-1]
        predicted_price = current_price * (1 + predicted_change / 100)

        confidence = min(0.95, 0.5 + abs(predicted_change) / 20)
        
        # Direction
        if predicted_change > 1.0:
            direction = "UP"
        elif predicted_change < -1.0:
            direction = "DOWN"
        else:
            direction = "STABLE"
        
        return {
            "symbol": symbol,
            "status": "predicted",
            "current_price": float(current_price),
            "predicted_change_percent": float(predicted_change),
            "predicted_price": float(predicted_price),
            "direction": direction,
            "confidence": float(confidence),
            "technical_indicators": {
                "RSI": float(df['RSI'].iloc[-1]),
                "MACD": float(df['MACD'].iloc[-1]),
                "BB_Position": float(df['BB_Position'].iloc[-1]),
                "Distance_MA20": float(df['Distance_MA20'].iloc[-1])
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def analyze_portfolio(self, symbols: List[str]) -> List[Dict]:
        logger.info(f"{self.name}: Analyzing {len(symbols)} stocks with ML model...")
        
        if not self.is_trained:
            self.load_model()
        
        if not self.is_trained:
            return [{
                "status": "error",
                "message": "Model not trained. Please train the model first."
            }]
        
        async with async_session_maker() as db:
            predictions = []
            for symbol in symbols:
                try:
                    prediction = await self.predict_price_movement(symbol, db)
                    predictions.append(prediction)
                    
                    if prediction.get("status") == "predicted":
                        logger.info(
                            f"{self.name}: {symbol} - "
                            f"Predicted: {prediction['direction']} "
                            f"({prediction['predicted_change_percent']:+.2f}%) "
                            f"Confidence: {prediction['confidence']:.0%}"
                        )
                except Exception as e:
                    logger.error(f"{self.name}: Error analyzing {symbol}: {e}")
                    predictions.append({
                        "symbol": symbol,
                        "status": "error",
                        "message": str(e)
                    })
        
        return predictions
    
    def extract_pattern_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        if len(data) < 20:
            return None
        
        try:
            recent = data.tail(20).copy()
            
            # price movement pattern (normalized)
            close_prices = recent['Close'].values
            normalized_prices = (close_prices - close_prices[0]) / close_prices[0]
            
            # volatility pattern
            returns = np.diff(close_prices) / close_prices[:-1]
            volatility = np.std(returns)
            
            # volume pattern (normalized)
            volumes = recent['Volume'].values
            normalized_volumes = volumes / np.max(volumes) if np.max(volumes) > 0 else volumes
            
            # technical indicators
            ma_5 = recent['Close'].rolling(5).mean().iloc[-1]
            ma_10 = recent['Close'].rolling(10).mean().iloc[-1]
            current_price = close_prices[-1]
            
            # combine features
            features = np.concatenate([
                normalized_prices[-10:],  # Last 10 days normalized prices
                [volatility],              # Volatility
                normalized_volumes[-5:],  # Last 5 days normalized volumes
                [(ma_5 - current_price) / current_price],  # Distance from MA5
                [(ma_10 - current_price) / current_price]  # Distance from MA10
            ])
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting pattern features: {e}")
            return None
    
    async def find_similar_stocks(
        self,
        target_symbol: str,
        candidate_symbols: List[str],
        dataset_dir: Path,
        top_n: int = 5
    ) -> List[Dict]:
        """
        Return list of similar stocks with similarity scores
        """
        try:
            target_csv = dataset_dir / f"{target_symbol}.csv"
            if not target_csv.exists():
                logger.error(f"CSV not found for {target_symbol}")
                return []
            
            target_data = await self.load_historical_data_from_csv(target_symbol, str(target_csv))
            if target_data.empty:
                return []
            
            target_features = self.extract_pattern_features(target_data)
            if target_features is None:
                return []
            
            similarities = []
            
            for candidate in candidate_symbols:
                if candidate == target_symbol:
                    continue
                
                candidate_csv = dataset_dir / f"{candidate}.csv"
                if not candidate_csv.exists():
                    continue
                
                candidate_data = await self.load_historical_data_from_csv(candidate, str(candidate_csv))
                if candidate_data.empty:
                    continue
                
                candidate_features = self.extract_pattern_features(candidate_data)
                if candidate_features is None:
                    continue
                
                # calculate cosine similarity
                from scipy.spatial.distance import cosine
                similarity = 1 - cosine(target_features, candidate_features)
                
                similarities.append({
                    'symbol': candidate,
                    'similarity_score': float(similarity),
                    'current_price': float(candidate_data['Close'].iloc[-1]),
                    'price_change_1d': float(
                        (candidate_data['Close'].iloc[-1] - candidate_data['Close'].iloc[-2]) 
                        / candidate_data['Close'].iloc[-2] * 100
                    ) if len(candidate_data) > 1 else 0.0
                })
            
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            logger.info(
                f"{self.name}: Found {len(similarities)} similar stocks to {target_symbol}, "
                f"returning top {top_n}"
            )
            
            return similarities[:top_n]
            
        except Exception as e:
            logger.error(f"Error finding similar stocks: {e}")
            return []
    
    async def find_similar_to_portfolio(
        self,
        portfolio_symbols: List[str],
        all_symbols: List[str],
        dataset_dir: Path,
        top_n: int = 10
    ) -> List[Dict]:
        """
        Find stocks similar to WINNING positions in portfolio
        Retun list of recommended stocks with similarity info
        """
        recommendations = {}
        
        for portfolio_symbol in portfolio_symbols:
            similar = await self.find_similar_stocks(
                portfolio_symbol,
                all_symbols,
                dataset_dir,
                top_n=5
            )
            
            for stock in similar:
                symbol = stock['symbol']
                if symbol not in portfolio_symbols: 
                    if symbol not in recommendations:
                        recommendations[symbol] = stock
                        recommendations[symbol]['similar_to'] = [portfolio_symbol]
                    else:
                        recommendations[symbol]['similar_to'].append(portfolio_symbol)
                        old_score = recommendations[symbol]['similarity_score']
                        new_score = stock['similarity_score']
                        recommendations[symbol]['similarity_score'] = (old_score + new_score) / 2
        
        result = list(recommendations.values())
        result.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return result[:top_n]

    async def predict_price_movement_from_db(self, symbol: str, db: AsyncSession) -> Dict:
        """Alias for predict_price_movement - gets data from database"""
        return await self.predict_price_movement(symbol, db)


market_monitor = MarketMonitoringAgent()
