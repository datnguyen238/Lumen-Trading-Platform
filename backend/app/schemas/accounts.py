from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal


class AccountCreate(BaseModel):
    user_id: int
    name: str = "Main"


class AccountRead(BaseModel):
    id: int
    user_id: int
    name: str
    cash_balance: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class PositionRead(BaseModel):
    id: int
    account_id: int
    symbol: str
    quantity: Decimal
    average_price: Decimal

    model_config = {"from_attributes": True}
