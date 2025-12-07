from pydantic import BaseModel, Field
from typing import List, Optional

# Request/Response Models
class TrainingRequest(BaseModel):
    symbols: Optional[List[str]] = None
    use_sample: bool = False
    
    
class TradingCycleRequest(BaseModel):
    symbols: List[str]
    use_csv: bool = False
    risk_tolerance: float = Field(default=0.5, ge=0.0, le=1.0, description="Risk tolerance: 0.0 (conservative) to 1.0 (aggressive)")


class RiskSettingsRequest(BaseModel):
    risk_tolerance: float = Field(ge=0.0, le=1.0, description="Risk tolerance: 0.0 (conservative) to 1.0 (aggressive)")


class SystemStatusResponse(BaseModel):
    status: str
    coordinator: dict
    