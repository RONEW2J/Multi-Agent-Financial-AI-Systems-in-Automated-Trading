import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    ALPHA_VANTAGE_API_KEY: str = ""
    MASSIVE_API_KEY: str = Field(default="", description="Massive API key for stock data")
    
    DB_HOST: str = Field(..., description="Database host")
    DB_PORT: int = Field(..., description="Database port")
    DB_USER: str = Field(..., description="Database user")
    DB_PASSWORD: str = Field(..., description="Database password")
    DB_NAME: str = Field(..., description="Database name")

    MARKET_AGENT_URL: str = "http://localhost:8000"
    DECISION_AGENT_URL: str = "http://localhost:8001"
    EXECUTION_AGENT_URL: str = "http://localhost:8002"
    
    DEFAULT_SYMBOL: str = "AAPL"
    MARKET_POLL_INTERVAL: int = 60
    DEFAULT_QUANTITY: float = 1.0

    MODEL_PATH: str = "./models/trading_model.pkl"
    MODEL_THRESHOLD_BUY: float = 0.6
    MODEL_THRESHOLD_SELL: float = 0.4

    LOG_LEVEL: str = "INFO"
    
    model_config = {
        "env_file": [".env", "../.env"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "case_sensitive": False
    }

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property  
    def database_url_sync(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def app_name(self) -> str:
        return "Multi-Agent Trading System"
    
    @property
    def app_version(self) -> str:
        return "1.0.0"

settings = Settings()