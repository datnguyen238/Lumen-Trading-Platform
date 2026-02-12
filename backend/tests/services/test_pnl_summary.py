from datetime import datetime
from decimal import Decimal

from app.api.summary import account_summary
from app.models.enums import OrderSide, OrderType
from app.models.models import PriceBar, Trade
from app.schemas.orders import OrderCreate
from app.services.execution import execute_market_order


def test_buy_buy_sell_realized_and_unrealized_pnl(db_session, account_with_price):
    # Two buys at 100 each (from fixture market price)
    execute_market_order(
        db_session,
        OrderCreate(
            account_id=account_with_price.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("2"),
        ),
    )
    execute_market_order(
        db_session,
        OrderCreate(
            account_id=account_with_price.id,
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("1"),
        ),
    )

    # Sell one at 130 via direct trade + fill path through execution using latest close
    db_session.add(
        PriceBar(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 8, 0, 0, 0),
            open=130,
            high=130,
            low=130,
            close=130,
            volume=1000,
        )
    )
    db_session.commit()

    execute_market_order(
        db_session,
        OrderCreate(
            account_id=account_with_price.id,
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("1"),
        ),
    )

    summary = account_summary(account_with_price.id, db_session)
    pos = summary.positions["AAPL"]

    # Realized: sold 1 at 130, avg cost 100 => +30
    assert summary.realized_pnl == Decimal("30")
    # Remaining 2 shares with avg 100 and mark 130 => +60 unrealized
    assert pos.quantity == Decimal("2")
    assert pos.avg_cost == Decimal("100")
    assert pos.mark_price == Decimal("130")
    assert summary.unrealized_pnl == Decimal("60")
    assert summary.total_pnl == Decimal("90")


def test_summary_handles_manual_trade_ordering(db_session, account_with_price):
    db_session.add(
        Trade(
            account_id=account_with_price.id,
            order_id=1,
            symbol="MSFT",
            side=OrderSide.BUY,
            quantity=Decimal("2"),
            price=Decimal("50"),
        )
    )
    db_session.add(
        Trade(
            account_id=account_with_price.id,
            order_id=2,
            symbol="MSFT",
            side=OrderSide.SELL,
            quantity=Decimal("1"),
            price=Decimal("70"),
        )
    )
    db_session.commit()

    summary = account_summary(account_with_price.id, db_session)
    assert summary.realized_pnl == Decimal("20")
