from pydantic import BaseModel
from decimal import Decimal
from typing import Optional
from datetime import datetime

from app.models.enums import OrderSide, OrderType, OrderStatus


class OrderCreate(BaseModel):
    account_id: int
    symbol: str
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal
    limit_price: Optional[Decimal] = None


class OrderRead(BaseModel):
    id: int
    account_id: int
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Optional[Decimal]
    status: OrderStatus
    filled_quantity: Decimal
    avg_fill_price: Optional[Decimal]
    created_at: datetime

    model_config = {"from_attributes": True}
