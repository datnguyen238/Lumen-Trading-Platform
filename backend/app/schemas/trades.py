from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from app.models.enums import OrderSide


class TradeRead(BaseModel):
    account_currency: str
    fx_rate: Decimal
    fx_timestamp: datetime | None = None
    fx_source: str
    native_total: Decimal
    account_total: Decimal
    account_price: Decimal
    id: int
    account_id: int
    order_id: int
    symbol: str
    currency: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    executed_at: datetime

    model_config = {"from_attributes": True}
