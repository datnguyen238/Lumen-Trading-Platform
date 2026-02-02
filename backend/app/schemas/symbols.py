from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SymbolAddRequest(BaseModel):
    symbol: str
    asset_type: str = "stock"  # stock/index/crypto


class SymbolRead(BaseModel):
    id: int
    symbol: str
    name: Optional[str] = None
    asset_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
