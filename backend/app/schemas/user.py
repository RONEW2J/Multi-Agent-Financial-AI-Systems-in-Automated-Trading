from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    initial_capital: float = 100000.0


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class BuyStockRequest(BaseModel):
    symbol: str
    shares: int
    price: Optional[float] = None


class SellStockRequest(BaseModel):
    symbol: str
    shares: int
    price: Optional[float] = None