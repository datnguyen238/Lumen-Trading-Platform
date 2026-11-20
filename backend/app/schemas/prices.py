from pydantic import BaseModel, Field, model_validator
from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional


class PriceBarRead(BaseModel):
    id: int
    symbol: str
    currency: str | None = None
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None
    change: Decimal | None = None
    change_percent: Decimal | None = None
    previous_timestamp: datetime | None = None

    model_config = {"from_attributes": True}


class DailyPriceRead(BaseModel):
    symbol: str
    currency: str | None = None
    interval: Literal["1d"] = "1d"
    session_date: date
    timestamp: datetime
    open: Decimal = Field(gt=0, allow_inf_nan=False)
    high: Decimal = Field(gt=0, allow_inf_nan=False)
    low: Decimal = Field(gt=0, allow_inf_nan=False)
    close: Decimal = Field(gt=0, allow_inf_nan=False)
    volume: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    source: Literal["yfinance"] = "yfinance"

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def valid_daily_range(self):
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid daily price range")
        return self


class LoadStockRequest(BaseModel):
    symbol: str
    start: date
    end: date
    interval: str = "1d"


class LoadCryptoRequest(BaseModel):
    symbol: str
    interval: str = "1d"
    limit: int = 500
