from pydantic import BaseModel
from decimal import Decimal
from typing import Dict


class SymbolPnL(BaseModel):
    symbol: str
    quantity: Decimal
    avg_cost: Decimal
    mark_price: Decimal
    unrealized_pnl: Decimal


class AccountSummary(BaseModel):
    account_id: int
    cash: Decimal
    equity: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    positions: Dict[str, SymbolPnL]
