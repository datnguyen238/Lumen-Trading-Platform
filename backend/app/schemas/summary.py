from pydantic import BaseModel
from decimal import Decimal
from typing import Dict
from datetime import datetime


class SymbolPnL(BaseModel):
    native_currency: str
    native_mark_price: Decimal
    fx_rate: Decimal
    fx_timestamp: datetime | None = None
    fx_source: str
    symbol: str
    currency: str
    quantity: Decimal
    avg_cost: Decimal
    mark_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    available_quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")


class AccountSummary(BaseModel):
    account_id: int
    currency: str
    cash: Decimal
    reserved_cash: Decimal = Decimal("0")
    available_cash: Decimal = Decimal("0")
    equity: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    positions: Dict[str, SymbolPnL]
