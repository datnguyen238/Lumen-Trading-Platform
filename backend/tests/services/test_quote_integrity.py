from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
import pandas as pd
from app.models.models import PriceBar
from app.services.price_refresh import _upsert_bar
from app.data import price_loader


def test_repeated_quote_upserts_are_atomic_and_keep_latest_values(db_session):
    when = datetime(2026, 11, 19, 20, 59)
    first = _upsert_bar(db_session, 'AAPL', when, 100, 105, 99, 101, 10)
    second = _upsert_bar(db_session, 'AAPL', when, 100, 105, 99, 104, 12)
    db_session.commit()
    assert first.id == second.id
    assert db_session.query(PriceBar).count() == 1
    assert db_session.query(PriceBar).one().close == Decimal('104')


def test_force_refresh_bypasses_inner_cache_and_normalizes_quote_time(monkeypatch):
    old = dict(symbol='AAPL', close=50)
    monkeypatch.setattr(price_loader, '_STOCK_CACHE', {'AAPL': (datetime.utcnow(), old)})
    frame = pd.DataFrame({'Open': [100], 'High': [102], 'Low': [99], 'Close': [101], 'Volume': [50]},
                         index=pd.DatetimeIndex(['2026-11-19 15:59'], tz='America/New_York'))
    monkeypatch.setattr(price_loader.yf, 'Ticker', lambda symbol: SimpleNamespace(history=lambda **kwargs: frame))
    assert price_loader.fetch_latest_stock_bar_yfinance('AAPL') is old
    fresh = price_loader.fetch_latest_stock_bar_yfinance('AAPL', force_refresh=True)
    assert fresh['close'] == 101
    assert fresh['timestamp'] == datetime(2026, 11, 19, 20, 59)
