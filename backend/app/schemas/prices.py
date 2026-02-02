from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
from typing import Optional


class PriceBarRead(BaseModel):
    id: int
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class LoadStockRequest(BaseModel):
    symbol: str
    start: date
    end: date
    interval: str = "1d"


class LoadCryptoRequest(BaseModel):
    symbol: str
    interval: str = "1d"
    limit: int = 500
