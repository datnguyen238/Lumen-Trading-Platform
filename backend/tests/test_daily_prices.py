from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from app.data import price_loader
from app.models.models import PriceBar


@pytest.fixture(autouse=True)
def isolated_daily_cache(monkeypatch):
    monkeypatch.setattr(price_loader, "_DAILY_STOCK_CACHE", OrderedDict())


def daily_frame(values=None, *, session="2026-11-19", tz="Asia/Ho_Chi_Minh"):
    values = values or {"Open": 56200, "High": 57000, "Low": 56000, "Close": 56700, "Volume": 12345}
    return pd.DataFrame({key: [value] for key, value in values.items()},
                        index=pd.DatetimeIndex([session], tz=tz))


def provider(monkeypatch, frame, currency="VND"):
    calls = []

    def ticker(symbol):
        def history(**kwargs):
            calls.append((symbol, kwargs))
            return frame
        return SimpleNamespace(history=history, get_history_metadata=lambda: {"currency": currency})

    monkeypatch.setattr(price_loader.yf, "Ticker", ticker)
    return calls


def test_daily_details_use_daily_feed_without_changing_latest_intraday(client, db_session, monkeypatch):
    intraday = PriceBar(symbol="VNM.VN", currency="VND", timestamp=datetime(2026, 11, 19, 7, 59),
                        open=56700, high=56700, low=56700, close=56700, volume=100)
    db_session.add(intraday)
    db_session.commit()
    calls = provider(monkeypatch, daily_frame())

    response = client.get("/prices/daily", params={"symbol": " vnm.vn "})
    assert response.status_code == 200
    body = response.json()
    assert {key: body[key] for key in ("symbol", "currency", "interval", "source")} == {
        "symbol": "VNM.VN", "currency": "VND", "interval": "1d", "source": "yfinance"}
    assert [Decimal(body[key]) for key in ("open", "high", "low", "close")] == [
        Decimal("56200"), Decimal("57000"), Decimal("56000"), Decimal("56700")]
    assert calls == [("VNM.VN", {"period": "5d", "interval": "1d", "auto_adjust": False, "timeout": 8})]
    assert client.get("/prices/daily", params={"symbol": "VNM.VN"}).json() == body
    assert len(calls) == 1
    assert db_session.query(PriceBar).count() == 1
    assert db_session.query(PriceBar).one().open == Decimal("56700")


def test_vietnam_session_date_is_captured_before_utc_conversion(monkeypatch):
    provider(monkeypatch, daily_frame())
    item = price_loader.fetch_daily_stock_bar_yfinance("VNM.VN")
    assert item.session_date == date(2026, 11, 19)
    assert item.timestamp == datetime(2026, 11, 18, 17)


def test_daily_prices_keep_decimal_precision_and_native_quote_units(client, monkeypatch):
    values = {"Open": Decimal("12.34567890123456789"), "High": Decimal("13.12345678901234567"),
              "Low": Decimal("11.12345678901234567"), "Close": Decimal("12.98765432109876543"), "Volume": 25}
    provider(monkeypatch, daily_frame(values, tz="Europe/London"), "GBp")
    response = client.get("/prices/daily", params={"symbol": "EXAMPLE.L"})
    assert response.status_code == 200
    assert response.json()["currency"] == "GBX"
    for key in ("open", "high", "low", "close"):
        assert response.json()[key] == str(values[key.capitalize()])


def test_expired_daily_data_is_not_used_during_provider_outage_and_failure_is_not_cached(client, db_session, monkeypatch):
    now = [100.0]
    monkeypatch.setattr(price_loader, "monotonic", lambda: now[0])
    provider(monkeypatch, daily_frame())
    assert client.get("/prices/daily", params={"symbol": "VNM.VN"}).status_code == 200
    db_session.add(PriceBar(symbol="VNM.VN", currency="VND", timestamp=datetime(2026, 11, 19, 7, 59),
                            open=56700, high=56700, low=56700, close=56700))
    db_session.commit()
    now[0] += 301

    def unavailable(_symbol):
        raise RuntimeError("Private provider failure")
    monkeypatch.setattr(price_loader.yf, "Ticker", unavailable)
    response = client.get("/prices/daily", params={"symbol": "VNM.VN"})
    assert response.status_code == 503
    assert "Private provider failure" not in response.text
    assert "VNM.VN" not in price_loader._DAILY_STOCK_CACHE

    calls = provider(monkeypatch, daily_frame())
    assert client.get("/prices/daily", params={"symbol": "VNM.VN"}).status_code == 200
    assert len(calls) == 1


@pytest.mark.parametrize("changes", [
    {"Open": float("nan")}, {"Close": float("inf")}, {"Low": 0},
    {"High": 55000}, {"Low": 56800},
])
def test_invalid_daily_ohlc_is_unavailable_and_never_cached(client, monkeypatch, changes):
    values = {"Open": 56200, "High": 57000, "Low": 56000, "Close": 56700, **changes}
    calls = provider(monkeypatch, daily_frame(values))
    for _ in range(2):
        assert client.get("/prices/daily", params={"symbol": "VNM.VN"}).status_code == 503
    assert len(calls) == 2
    assert not price_loader._DAILY_STOCK_CACHE


def test_empty_daily_feed_does_not_use_intraday_cache(client, monkeypatch):
    monkeypatch.setattr(price_loader, "_STOCK_CACHE", {"AAPL": (datetime.utcnow(), {"close": 200})})
    calls = provider(monkeypatch, pd.DataFrame(), "USD")
    assert client.get("/prices/daily", params={"symbol": "AAPL"}).status_code == 503
    assert len(calls) == 1
    assert not price_loader._DAILY_STOCK_CACHE


def test_flat_daily_session_is_valid_without_inventing_currency(monkeypatch):
    values = {"Open": 56700, "High": 56700, "Low": 56700, "Close": 56700, "Volume": float("nan")}
    provider(monkeypatch, daily_frame(values), None)
    item = price_loader.fetch_daily_stock_bar_yfinance("UNKNOWN.X")
    assert item.open == item.high == item.low == item.close == Decimal("56700")
    assert item.currency is None
    assert item.volume is None


def test_daily_cache_evicts_least_recently_used_symbol(monkeypatch):
    monkeypatch.setattr(price_loader, "_DAILY_STOCK_CACHE_SIZE", 2)
    calls = provider(monkeypatch, daily_frame())
    for symbol in ("AAA", "BBB", "AAA", "CCC", "BBB"):
        price_loader.fetch_daily_stock_bar_yfinance(symbol)
    assert [symbol for symbol, _ in calls] == ["AAA", "BBB", "CCC", "BBB"]
    assert len(price_loader._DAILY_STOCK_CACHE) == 2
