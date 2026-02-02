from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from app.models.enums import OrderSide


class TradeRead(BaseModel):
    id: int
    account_id: int
    order_id: int
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    executed_at: datetime

    model_config = {"from_attributes": True}
