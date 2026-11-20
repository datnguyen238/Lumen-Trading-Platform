from collections import OrderedDict
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from app.data import price_loader
from app.models.models import PriceBar


@pytest.fixture(autouse=True)
def range_clock_and_cache(monkeypatch):
    current = [datetime(2026, 11, 20, 1, tzinfo=timezone.utc)]

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return current[0].astimezone(tz) if tz else current[0].replace(tzinfo=None)

    monkeypatch.setattr(price_loader, "datetime", Clock)
    monkeypatch.setattr(price_loader, "_PRICE_RANGE_CACHE", OrderedDict())
    return current


def range_frame(rows=None, tz="Asia/Ho_Chi_Minh"):
    rows = rows or [("2026-11-19", 110, 120, 100, 115), ("2026-11-20", 112, 125, 105, 118)]
    return pd.DataFrame([row[1:] for row in rows], columns=["Open", "High", "Low", "Close"],
                        index=pd.DatetimeIndex([row[0] for row in rows], tz=tz))


def provider(monkeypatch, frame, currency="VND"):
    calls = []

    def ticker(symbol):
        def history(**kwargs):
            calls.append((symbol, kwargs))
            return frame
        return SimpleNamespace(history=history, get_history_metadata=lambda: {"currency": currency})

    monkeypatch.setattr(price_loader.yf, "Ticker", ticker)
    return calls


def test_range_aggregates_daily_highs_lows_without_reading_or_writing_intraday_prices(client, db_session, monkeypatch):
    db_session.add(PriceBar(symbol="VNM.VN", currency="VND", timestamp=datetime(2026, 11, 20),
                            open=999, high=999, low=999, close=999))
    db_session.commit()
    calls = provider(monkeypatch, range_frame([
        ("2026-11-20", 112, 125, 80, 118),
        ("2026-11-19", 110, 145, 100, 115),
    ]))
    response = client.get("/prices/range", params={"symbol": " vnm.vn ", "days": 30})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "symbol": "VNM.VN", "currency": "VND", "interval": "1d", "days": 30,
        "window_start_date": "2026-10-22", "window_end_date": "2026-11-20", "timezone": "Asia/Ho_Chi_Minh",
        "start_date": "2026-11-19", "end_date": "2026-11-20", "low": "80", "high": "145",
        "observations": 2, "source": "yfinance",
    }
    assert calls == [("VNM.VN", {"start": date(2026, 10, 19), "end": date(2026, 11, 22),
                                 "interval": "1d", "auto_adjust": False, "keepna": True, "timeout": 8})]
    assert db_session.query(PriceBar).count() == 1
    assert db_session.query(PriceBar).one().close == 999


@pytest.mark.parametrize("tz,start,end,low,high,observations", [
    ("Asia/Ho_Chi_Minh", "2026-11-14", "2026-11-20", "50", "400", 3),
    ("America/New_York", "2026-11-13", "2026-11-19", "10", "300", 3),
])
def test_range_uses_exchange_local_calendar_dates_and_excludes_outside_bars(
    client, monkeypatch, tz, start, end, low, high, observations,
):
    calls = provider(monkeypatch, range_frame([
        ("2026-11-13", 110, 300, 10, 115),
        ("2026-11-14", 110, 120, 80, 115),
        ("2026-11-19", 110, 130, 90, 115),
        ("2026-11-20", 110, 400, 50, 115),
    ], tz=tz))
    body = client.get("/prices/range", params={"symbol": "VNM.VN", "days": 7}).json()
    assert (body["start_date"], body["end_date"], body["low"], body["high"], body["observations"]) == (
        start, end, low, high, observations)
    assert (body["window_start_date"], body["window_end_date"], body["timezone"]) == (start, end, tz)
    assert calls[0][1]["interval"] == "1d"


def test_partial_listing_history_returns_actual_observation_dates(client, monkeypatch):
    provider(monkeypatch, range_frame())
    body = client.get("/prices/range", params={"symbol": "NEW.VN", "days": 365}).json()
    assert body["days"] == 365
    assert (body["window_start_date"], body["window_end_date"], body["timezone"]) == (
        "2025-11-21", "2026-11-20", "Asia/Ho_Chi_Minh")
    assert (body["start_date"], body["end_date"], body["observations"]) == ("2026-11-19", "2026-11-20", 2)


def test_range_preserves_native_currency_units_and_decimal_precision(client, monkeypatch):
    low, high = Decimal("11.12345678901234567"), Decimal("13.12345678901234567")
    provider(monkeypatch, range_frame([("2026-11-20", Decimal("12.34567890123456789"),
                                      high, low, Decimal("12.98765432109876543"))], tz="Europe/London"), "GBp")
    response = client.get("/prices/range", params={"symbol": "EXAMPLE.L", "days": 30})
    assert response.status_code == 200
    assert response.json()["currency"] == "GBX"
    assert response.json()["low"] == str(low)
    assert response.json()["high"] == str(high)


@pytest.mark.parametrize("days", [7, 30, 90, 180, 365])
def test_supported_calendar_ranges(client, monkeypatch, days):
    provider(monkeypatch, range_frame())
    response = client.get("/prices/range", params={"symbol": "VNM.VN", "days": days})
    assert response.status_code == 200
    assert response.json()["days"] == days


@pytest.mark.parametrize("params", [
    {"symbol": "NVDA", "days": 1}, {"symbol": "NVDA", "days": 14},
    {"symbol": "NVDA", "days": 366}, {"symbol": "NVDA", "days": "7.5"},
    {"symbol": "NVDA", "days": "week"}, {"symbol": " "}, {"symbol": "A" * 41},
])
def test_invalid_range_queries_do_not_request_provider_data(client, monkeypatch, params):
    calls = provider(monkeypatch, range_frame())
    assert client.get("/prices/range", params=params).status_code == 422
    assert not calls


@pytest.mark.parametrize("values", [
    (110, float("nan"), 100, 115), (110, 120, -1, 115),
    (110, 120, 100, float("inf")), (0, 120, 100, 115),
    (110, 109, 100, 115), (110, 120, 116, 115),
    (float("nan"), float("nan"), float("nan"), float("nan")),
])
def test_invalid_in_window_daily_bar_fails_entire_range_and_is_not_cached(client, monkeypatch, values):
    calls = provider(monkeypatch, range_frame([
        ("2026-11-19", 110, 120, 100, 115), ("2026-11-20", *values),
    ]))
    for _ in range(2):
        assert client.get("/prices/range", params={"symbol": "VNM.VN"}).status_code == 503
    assert len(calls) == 2
    assert not price_loader._PRICE_RANGE_CACHE


def test_invalid_bar_outside_window_does_not_change_observed_range(client, monkeypatch):
    provider(monkeypatch, range_frame([
        ("2026-11-01", 0, 0, 0, 0), ("2026-11-20", 110, 120, 100, 115),
    ]))
    response = client.get("/prices/range", params={"symbol": "VNM.VN", "days": 7})
    assert response.status_code == 200
    assert response.json()["observations"] == 1


@pytest.mark.parametrize("frame", [
    pd.DataFrame(),
    range_frame([("2026-10-01", 110, 120, 100, 115)]),
    range_frame(tz=None),
    range_frame([("2026-11-20", 110, 120, 100, 115), ("2026-11-20", 110, 130, 100, 115)]),
])
def test_missing_ambiguous_or_duplicate_daily_data_does_not_fall_back_to_stored_quotes(
    client, db_session, monkeypatch, frame,
):
    db_session.add(PriceBar(symbol="VNM.VN", currency="VND", timestamp=datetime(2026, 11, 20),
                            open=999, high=999, low=999, close=999))
    db_session.commit()
    provider(monkeypatch, frame)
    assert client.get("/prices/range", params={"symbol": "VNM.VN"}).status_code == 503
    assert not price_loader._PRICE_RANGE_CACHE
    assert db_session.query(PriceBar).one().close == 999


def test_expired_range_is_unavailable_during_outage_and_failure_is_not_cached(client, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(price_loader, "monotonic", lambda: clock[0])
    provider(monkeypatch, range_frame())
    assert client.get("/prices/range", params={"symbol": "VNM.VN"}).status_code == 200
    clock[0] += 301

    def unavailable(_symbol):
        raise RuntimeError("Private provider error")
    monkeypatch.setattr(price_loader.yf, "Ticker", unavailable)
    response = client.get("/prices/range", params={"symbol": "VNM.VN"})
    assert response.status_code == 503
    assert "Private provider error" not in response.text
    assert not price_loader._PRICE_RANGE_CACHE
    calls = provider(monkeypatch, range_frame())
    assert client.get("/prices/range", params={"symbol": "VNM.VN"}).status_code == 200
    assert len(calls) == 1


def test_range_cache_is_keyed_by_normalized_symbol_and_days_and_bounded(client, monkeypatch):
    monkeypatch.setattr(price_loader, "_PRICE_RANGE_CACHE_SIZE", 2)
    calls = provider(monkeypatch, range_frame())
    for symbol, days in [(" vnm.vn ", 7), ("VNM.VN", 7), ("VNM.VN", 30), ("VNM.VN", 7),
                         ("FPT.VN", 7), ("VNM.VN", 30)]:
        assert client.get("/prices/range", params={"symbol": symbol, "days": days}).status_code == 200
    assert [(symbol, kwargs["start"]) for symbol, kwargs in calls] == [
        ("VNM.VN", date(2026, 11, 11)), ("VNM.VN", date(2026, 10, 19)),
        ("FPT.VN", date(2026, 11, 11)), ("VNM.VN", date(2026, 10, 19)),
    ]
    assert len(price_loader._PRICE_RANGE_CACHE) == 2


def test_range_cache_expires_at_market_local_midnight(client, monkeypatch, range_clock_and_cache):
    range_clock_and_cache[0] = datetime(2026, 11, 19, 16, 59, tzinfo=timezone.utc)
    clock = [100.0]
    monkeypatch.setattr(price_loader, "monotonic", lambda: clock[0])
    calls = provider(monkeypatch, range_frame([
        ("2026-11-13", 110, 999, 100, 115),
        ("2026-11-19", 110, 120, 100, 115),
        ("2026-11-20", 110, 150, 100, 115),
    ]))
    before = client.get("/prices/range", params={"symbol": "VNM.VN", "days": 7}).json()
    assert before["high"] == "999"
    assert (before["window_start_date"], before["window_end_date"]) == ("2026-11-13", "2026-11-19")
    range_clock_and_cache[0] = datetime(2026, 11, 19, 17, 1, tzinfo=timezone.utc)
    clock[0] += 120
    after = client.get("/prices/range", params={"symbol": "VNM.VN", "days": 7}).json()
    assert (after["start_date"], after["end_date"], after["high"]) == ("2026-11-19", "2026-11-20", "150")
    assert (after["window_start_date"], after["window_end_date"], after["timezone"]) == (
        "2026-11-14", "2026-11-20", "Asia/Ho_Chi_Minh")
    assert len(calls) == 2
