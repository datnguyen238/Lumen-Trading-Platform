from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.models import Account, Position, Order, Trade, PriceBar, User
from app.schemas.accounts import AccountRead, PositionRead
from app.schemas.orders import OrderRead
from app.schemas.trades import TradeRead
from app.schemas.summary import AccountSummary
from app.services.auth import current_user, owned_account
from app.services.portfolio import build_summary

router = APIRouter()


class Overview(BaseModel):
    account: AccountRead
    positions: list[PositionRead]
    summary: AccountSummary
    orders: list[OrderRead]
    trades: list[TradeRead]
    quotes: list[dict]


@router.get('/accounts/{account_id}/overview', response_model=Overview)
def overview(account_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_account(account_id, db, user)
    # Execution locks the same account, so balances and fills cannot straddle a trade.
    account = db.query(Account).filter(Account.id == account_id).populate_existing().with_for_update(read=True).one()
    positions = db.query(Position).filter(Position.account_id == account_id).order_by(Position.symbol).all()
    try:
        summary = build_summary(db, account)
    except ValueError as error:
        raise HTTPException(409, str(error)) from None
    quotes = []
    for position in positions:
        if position.quantity <= 0:
            continue
        row = db.query(PriceBar).filter(PriceBar.symbol == position.symbol).order_by(PriceBar.timestamp.desc()).first()
        if row:
            quotes.append({'symbol': row.symbol, 'currency': row.currency, 'close': str(row.close), 'timestamp': row.timestamp.isoformat(), 'source': 'stored_market_bar'})
    return Overview(account=account, positions=positions, summary=summary,
        orders=db.query(Order).filter(Order.account_id == account_id).order_by(Order.created_at.desc(), Order.id.desc()).all(),
        trades=db.query(Trade).filter(Trade.account_id == account_id).order_by(Trade.executed_at.desc(), Trade.id.desc()).all(), quotes=quotes)
