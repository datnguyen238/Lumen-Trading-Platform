from pydantic import BaseModel, Field, model_validator
from decimal import Decimal
from typing import Optional
from datetime import datetime

from app.models.enums import OrderSide, OrderType, OrderStatus


class OrderCreate(BaseModel):
    account_id: int
    symbol: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z^][A-Za-z0-9.^=\-]{0,19}$")
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
    limit_price: Optional[Decimal] = Field(default=None, gt=0, max_digits=18, decimal_places=6, allow_inf_nan=False)
    client_order_id: str | None = Field(default=None, min_length=16, max_length=64)


class ExecutionRead(BaseModel):
    currency: str
    account_currency: str
    fx_rate: Decimal
    fx_timestamp: datetime | None = None
    fx_source: str
    account_price: Decimal
    account_total: Decimal
    quote_timestamp: datetime
    quote_price: Decimal
    cash_before: Decimal
    cash_after: Decimal
    fees: Decimal
    model: str
    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    account_currency: str
    fx_rate: Decimal
    fx_timestamp: datetime | None = None
    fx_source: str
    native_total: Decimal | None = None
    account_total: Decimal | None = None
    id: int
    account_id: int
    symbol: str
    currency: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Optional[Decimal]
    status: OrderStatus
    filled_quantity: Decimal
    avg_fill_price: Optional[Decimal]
    created_at: datetime
    execution: ExecutionRead | None = None

    model_config = {"from_attributes": True}


class PreviewRequest(BaseModel):
    account_id: int = Field(gt=0)
    symbol: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z][A-Za-z0-9.\-=]{0,19}$")
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=4)
    notional: Decimal | None = Field(default=None, ge=1, max_digits=14, decimal_places=2)
    limit_price: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)

    @model_validator(mode="after")
    def check_order(self):
        if (self.quantity is None) == (self.notional is None):
            raise ValueError("Enter either an amount or a number of shares.")
        if self.notional is not None and (self.side != OrderSide.BUY or self.order_type != OrderType.MARKET):
            raise ValueError("Amount entry is available for market buys. Use shares for this order.")
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("Enter your limit price.")
        if self.order_type == OrderType.MARKET and self.limit_price is not None:
            raise ValueError("Market orders do not use a limit price.")
        return self


class PreviewRead(BaseModel):
    account_currency: str
    fx_rate: Decimal
    fx_timestamp: datetime | None = None
    fx_source: str
    native_total: Decimal
    id: str
    account_id: int
    symbol: str
    currency: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    notional: Decimal | None
    limit_price: Decimal | None
    estimated_price: Decimal
    estimated_total: Decimal
    quote_timestamp: datetime
    expires_at: datetime
    cash_before: Decimal
    cash_after: Decimal
    shares_before: Decimal
    shares_after: Decimal
    available_cash: Decimal
    available_shares: Decimal
    fees: Decimal = Decimal("0")
    explanation: str


class ConfirmRequest(BaseModel):
    preview_id: str = Field(min_length=32, max_length=64)
