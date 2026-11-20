"""Cross-market execution keeps quotes native and every cash/P&L amount in base units."""
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models.enums import OrderSide, OrderStatus, OrderType
from app.models.models import Account, ExecutionDetail, FxRate, Order, OrderPreview, Position, Trade
from app.services.execution import process_pending_limit_orders
from app.services.price_refresh import _upsert_bar
from app.services.fx import get_fx_quote
from app.db.migrations import migrate_currencies, missing_currency_columns
from app.db.base import Base
from test_auth_trading_api import signup
from test_currencies import quote, preview, confirm, vnd_signup


def fx(db, rate='0.00004', source='VND', target='USD', when=None, updated=None):
    stamp = when or datetime.utcnow()
    row = db.get(FxRate, (source, target))
    values = dict(rate=Decimal(rate), timestamp=stamp, updated_at=updated or datetime.utcnow(), source='test-market-feed')
    if row:
        for key, value in values.items():
            setattr(row, key, value)
    else:
        row = FxRate(from_currency=source, to_currency=target, **values)
        db.add(row)
    db.commit()
    return row


def test_one_usd_portfolio_buys_us_and_vietnam_stocks_without_relabeling_quotes(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    quote(db_session, symbol='AAPL', price=100, currency='USD')
    fx(db_session)
    reviewed = preview(client, account_id, quantity=10)
    data = reviewed.json()
    assert reviewed.status_code == 200, reviewed.text
    assert data['currency'] == 'VND' and data['account_currency'] == 'USD'
    assert Decimal(data['estimated_price']) == 52000
    assert Decimal(data['native_total']) == 520000
    assert Decimal(data['estimated_total']) == Decimal('20.8')
    assert Decimal(data['cash_after']) == Decimal('99979.2')
    assert Decimal(data['fx_rate']) == Decimal('.00004')
    assert data['fx_timestamp'] and data['fx_source'] == 'test-market-feed'
    first = confirm(client, reviewed)
    assert first['currency'] == 'VND' and first['account_currency'] == 'USD'
    assert Decimal(first['avg_fill_price']) == 52000
    assert Decimal(first['account_total']) == Decimal('20.8')
    assert Decimal(first['fx_rate']) == Decimal('.00004')
    receipt = first['execution']
    assert Decimal(receipt['cash_before']) == 100000
    assert Decimal(receipt['cash_after']) == Decimal('99979.2')
    # A native USD fill shares this same account and does not invoke conversion.
    us = client.post('/orders/', json={'account_id': account_id, 'symbol': 'AAPL', 'side': 'BUY', 'quantity': '2.5'})
    assert us.status_code == 200, us.text
    assert us.json()['currency'] == 'USD'
    assert Decimal(us.json()['fx_rate']) == 1
    overview = client.get(f'/accounts/{account_id}/overview').json()
    assert {p['symbol'] for p in overview['positions']} == {'AAPL', 'VNM.VN'}
    assert Decimal(overview['summary']['cash']) == Decimal('99729.2')
    assert Decimal(overview['summary']['equity']) == 100000
    vn = overview['summary']['positions']['VNM.VN']
    assert vn['currency'] == 'USD' and vn['native_currency'] == 'VND'
    assert Decimal(vn['avg_cost']) == Decimal('2.08')
    assert Decimal(vn['native_mark_price']) == 52000
    assert Decimal(vn['mark_price']) == Decimal('2.08')
    assert client.post('/orders/confirm', json={'preview_id': data['id']}).json()['id'] == first['id']
    assert db_session.query(Trade).count() == 2
    assert {a['currency'] for a in client.get('/auth/me').json()['accounts']} == {'USD'}


def test_sell_uses_current_fx_but_realized_cost_uses_historical_fill_fx(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    bought = confirm(client, preview(client, account_id, quantity=10))
    quote(db_session, 55000, when=datetime.utcnow()+timedelta(seconds=1))
    fx(db_session, '.00005')
    sold = confirm(client, preview(client, account_id, side='SELL', quantity=4))
    assert Decimal(sold['avg_fill_price']) == 55000
    assert Decimal(sold['account_total']) == 11
    assert Decimal(sold['fx_rate']) == Decimal('.00005')
    data = client.get(f'/accounts/{account_id}/overview').json()
    summary = data['summary']
    assert summary['currency'] == 'USD'
    assert Decimal(summary['cash']) == Decimal('99990.2')
    assert Decimal(summary['realized_pnl']) == Decimal('2.68')
    assert Decimal(summary['unrealized_pnl']) == Decimal('4.02')
    assert Decimal(summary['total_pnl']) == Decimal('6.7')
    assert Decimal(summary['equity']) == Decimal('100006.7')
    trades = {t['side']: t for t in data['trades']}
    assert Decimal(trades['BUY']['price']) == 52000
    assert Decimal(trades['BUY']['fx_rate']) == Decimal('.00004')
    assert Decimal(trades['SELL']['fx_rate']) == Decimal('.00005')
    # Updating the current FX quote cannot mutate the recorded execution receipt.
    stored = db_session.get(Order, bought['id'])
    assert Decimal(stored.fx_rate) == Decimal('.00004')


def test_fx_movement_changes_unrealized_return_even_when_native_stock_price_is_flat(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    confirm(client, preview(client, account_id, quantity=2))
    fx(db_session, '.00005')
    summary = client.get(f'/accounts/{account_id}/summary').json()
    assert Decimal(summary['realized_pnl']) == 0
    assert Decimal(summary['unrealized_pnl']) == Decimal('1.04')
    assert Decimal(summary['positions']['VNM.VN']['native_mark_price']) == 52000


def test_base_currency_budget_reprices_both_stock_and_fx_without_exceeding_budget(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    reviewed = preview(client, account_id, notional=10)
    assert reviewed.status_code == 200, reviewed.text
    assert Decimal(reviewed.json()['quantity']) == 4
    assert Decimal(reviewed.json()['estimated_total']) == Decimal('8.32')
    quote(db_session, 60000, when=datetime.utcnow()+timedelta(seconds=1))
    fx(db_session, '.00005')
    filled = confirm(client, reviewed)
    assert Decimal(filled['filled_quantity']) == 3
    assert Decimal(filled['account_total']) == 9
    assert Decimal(filled['execution']['cash_after']) == 99991
    assert Decimal(filled['account_total']) <= 10


def test_budget_precision_uses_base_currency_and_share_precision_uses_native_market(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    # A fractional USD cash budget is valid even though the investment uses VND.
    reviewed = preview(client, account_id, notional='2.50')
    assert reviewed.status_code == 200, reviewed.text
    assert Decimal(reviewed.json()['quantity']) == 1
    confirm(client, reviewed)
    assert preview(client, account_id, quantity='1.5').status_code == 400
    assert preview(client, account_id, quantity=1, order_type='LIMIT', limit_price='50000.5').status_code == 400


def test_vnd_base_can_buy_fractional_us_shares_and_convert_sale_proceeds(client, db_session):
    account_id = vnd_signup(client)['accounts'][0]['id']
    quote(db_session, symbol='AAPL', price=100, currency='USD')
    fx(db_session, '25000', source='USD', target='VND')
    reviewed = preview(client, account_id, symbol='AAPL', notional=500000)
    assert reviewed.status_code == 200, reviewed.text
    assert Decimal(reviewed.json()['quantity']) == Decimal('.2')
    order = confirm(client, reviewed)
    assert order['currency'] == 'USD' and order['account_currency'] == 'VND'
    assert Decimal(order['filled_quantity']) * Decimal(order['avg_fill_price']) == 20
    assert Decimal(order['account_total']) == 500000
    assert Decimal(order['execution']['cash_after']) == 999500000
    assert preview(client, account_id, symbol='AAPL', notional='500000.5').status_code == 400
    sold = confirm(client, preview(client, account_id, symbol='AAPL', side='SELL', quantity='.1'))
    assert Decimal(sold['execution']['cash_after']) == 999750000


def test_native_limit_price_reserves_base_cash_and_cancellation_releases_it(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    order = confirm(client, preview(client, account_id, quantity=100, order_type='LIMIT', limit_price=50000))
    assert order['status'] == 'PENDING'
    assert Decimal(order['limit_price']) == 50000
    summary = client.get(f'/accounts/{account_id}/summary').json()
    assert Decimal(summary['reserved_cash']) == 200
    assert Decimal(summary['available_cash']) == 99800
    assert client.post(f"/orders/{order['id']}/cancel").status_code == 200
    assert Decimal(client.get(f'/accounts/{account_id}/summary').json()['reserved_cash']) == 0


def test_worker_rechecks_fx_and_cash_atomically_before_filling(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    account = db_session.get(Account, account_id)
    account.cash_balance = 3
    db_session.commit()
    quote(db_session)
    fx(db_session)
    order = confirm(client, preview(client, account_id, quantity=1, order_type='LIMIT', limit_price=50000))
    assert order['status'] == 'PENDING'
    # Native quote crosses the limit, but FX now makes the fill unaffordable.
    quote(db_session, 49000, when=datetime.utcnow()+timedelta(seconds=1))
    fx(db_session, '.0001')
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 0
    db_session.refresh(account)
    assert account.cash_balance == 3
    assert db_session.query(Trade).count() == db_session.query(Position).count() == 0
    assert db_session.get(Order, order['id']).status == OrderStatus.PENDING
    fx(db_session, '.00005')
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 1
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 0
    db_session.refresh(account)
    assert account.cash_balance == Decimal('.55')
    assert Decimal(db_session.query(Trade).one().fx_rate) == Decimal('.00005')


def test_confirmation_rejects_missing_fx_without_consuming_preview_or_cash(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    rate = fx(db_session)
    reviewed = preview(client, account_id, quantity=2)
    assert reviewed.status_code == 200, reviewed.text
    db_session.delete(rate); db_session.commit()
    result = client.post('/orders/confirm', json={'preview_id': reviewed.json()['id']})
    assert result.status_code == 400, result.text
    assert db_session.query(Trade).count() == db_session.query(Order).count() == 0
    assert db_session.get(Account, account_id).cash_balance == 100000
    assert db_session.get(OrderPreview, reviewed.json()['id']).order_id is None


@pytest.mark.parametrize('rate,age', [('0', 0), ('-0.00004', 0), ('0.00004', 8), ('0.00004', -1)])
def test_invalid_stale_or_future_fx_never_authorizes_cash_movement(client, db_session, rate, age):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session, rate, when=datetime.utcnow()-timedelta(days=age))
    with pytest.raises(ValueError):
        get_fx_quote(db_session, 'VND', 'USD')
    assert db_session.query(Trade).count() == db_session.query(Order).count() == 0
    assert db_session.get(Account, account_id).cash_balance == 100000


def test_fx_migration_is_additive_idempotent_and_keeps_legacy_fill_units(db_session, account_with_price):
    account = account_with_price
    order = Order(account_id=account.id, symbol='AAPL', side=OrderSide.BUY, order_type=OrderType.MARKET,
        quantity=1, filled_quantity=1, avg_fill_price=100, status=OrderStatus.FILLED)
    db_session.add(order); db_session.flush()
    trade = Trade(account_id=account.id, order_id=order.id, symbol='AAPL', side=OrderSide.BUY, quantity=1, price=100)
    db_session.add(trade)
    db_session.add(ExecutionDetail(order_id=order.id, quote_timestamp=datetime.utcnow(), quote_price=100,
        cash_before=10100, cash_after=10000, fees=0))
    db_session.flush()
    order_id, trade_id = order.id, trade.id
    db_session.commit()
    engine = db_session.get_bind()
    db_session.expire_all()
    with engine.begin() as connection:
        for table in ('orders', 'trades', 'order_previews', 'execution_details'):
            for column in ('native_currency', 'fx_rate', 'fx_timestamp', 'fx_source'):
                connection.execute(text(f'ALTER TABLE {table} DROP COLUMN {column}'))
        for table in ('trades', 'execution_details'):
            connection.execute(text(f'ALTER TABLE {table} DROP COLUMN account_value'))
        connection.execute(text('DROP TABLE fx_rates'))
        assert missing_currency_columns(connection)
    # This is the same order as explicit app.db.bootstrap, not DDL on a request.
    Base.metadata.create_all(engine)
    migrate_currencies(engine); migrate_currencies(engine)
    with engine.connect() as connection:
        assert not missing_currency_columns(connection)
        assert connection.execute(text('SELECT cash_balance FROM accounts WHERE id=:id'), {'id': account.id}).scalar() == 10000
        assert connection.execute(text('SELECT price, quantity, fx_rate FROM trades WHERE id=:id'), {'id': trade_id}).one() == (100, 1, 1)
        assert connection.execute(text('SELECT quote_price, cash_before, cash_after FROM execution_details WHERE order_id=:id'), {'id': order_id}).one() == (100, 10100, 10000)
    db_session.expire_all()
    migrated = db_session.get(Trade, trade_id)
    assert migrated.currency == migrated.account_currency == 'USD'
    assert migrated.account_total == 100


def test_fx_refresh_stores_both_observed_directions_and_reuses_fresh_cache(db_session, monkeypatch):
    from app.services import fx as fx_service
    calls = []
    observed_at = datetime.utcnow()
    def observed():
        # Provider waits must happen after SQL reads release their transaction.
        assert not db_session.in_transaction()
        calls.append(True)
        return Decimal('25000'), observed_at
    monkeypatch.setattr(fx_service, '_fetch_usd_vnd', observed)
    converted = fx_service.refresh_fx_quote(db_session, 'VND', 'USD')
    assert converted.rate == Decimal('.00004')
    assert converted.timestamp == observed_at
    assert converted.source == 'yfinance:USDVND=X'
    assert fx_service.get_fx_quote(db_session, 'USD', 'VND').rate == 25000
    assert fx_service.refresh_fx_quote(db_session, 'VND', 'USD').rate == Decimal('.00004')
    assert len(calls) == 1
    same = fx_service.get_fx_quote(db_session, 'USD', 'USD')
    assert same.rate == 1 and same.source == 'same_currency'
    assert len(calls) == 1


def test_fx_outage_can_use_recent_observation_but_never_an_expired_rate(db_session, monkeypatch):
    from app.services import fx as fx_service
    rate = fx(db_session, updated=datetime.utcnow()-timedelta(minutes=10))
    def outage():
        raise RuntimeError('provider unavailable')
    monkeypatch.setattr(fx_service, '_fetch_usd_vnd', outage)
    assert fx_service.refresh_fx_quote(db_session, 'VND', 'USD').rate == Decimal('.00004')
    rate.timestamp = datetime.utcnow()-timedelta(days=8)
    db_session.commit()
    with pytest.raises(ValueError, match='exchange rate'):
        fx_service.refresh_fx_quote(db_session, 'VND', 'USD')
    assert db_session.query(Trade).count() == 0


def test_vnd_conversion_rounding_matches_cash_receipt_and_cost_basis(client, db_session):
    account_id = vnd_signup(client)['accounts'][0]['id']
    quote(db_session, symbol='AAPL', price=1, currency='USD')
    fx(db_session, '25000', source='USD', target='VND')
    # A supported fractional USD share has an exact conversion of 2.5 VND.
    # Whole-dong accounting must use the same rounded debit everywhere.
    order = confirm(client, preview(client, account_id, symbol='AAPL', quantity='.0001'))
    debit = Decimal(order['account_total'])
    assert debit == 3
    assert Decimal(order['execution']['cash_after']) == Decimal('999999997')
    assert Decimal(order['execution']['cash_before']) - Decimal(order['execution']['cash_after']) == debit
    trade = db_session.query(Trade).one()
    position = db_session.query(Position).one()
    assert trade.account_total == debit
    assert Decimal(position.average_price) * Decimal(position.quantity) == debit


def test_completed_order_and_preview_retries_return_receipts_during_fx_outage(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    body = {'account_id': account_id, 'symbol': 'VNM.VN', 'side': 'BUY', 'quantity': 1,
        'client_order_id': 'completed-fx-order-key'}
    direct = client.post('/orders/', json=body)
    assert direct.status_code == 200, direct.text
    reviewed = preview(client, account_id, quantity=2)
    completed = confirm(client, reviewed)
    before = Decimal(db_session.get(Account, account_id).cash_balance)
    db_session.query(FxRate).delete(); db_session.commit()
    # A receipt is authoritative even when quotes cannot be refreshed now.
    retried_direct = client.post('/orders/', json=body)
    retried_preview = client.post('/orders/confirm', json={'preview_id': reviewed.json()['id']})
    assert retried_direct.status_code == 200, retried_direct.text
    assert retried_preview.status_code == 200, retried_preview.text
    assert retried_direct.json()['id'] == direct.json()['id']
    assert retried_preview.json()['id'] == completed['id']
    assert db_session.query(Trade).count() == 2
    assert Decimal(db_session.get(Account, account_id).cash_balance) == before
    assert client.post('/orders/', json={**body, 'quantity': 2}).status_code == 400


def test_legacy_pending_order_cannot_be_reinterpreted_in_a_different_currency(client, db_session):
    account_id = signup(client)['accounts'][0]['id']
    quote(db_session)
    fx(db_session)
    old = Order(account_id=account_id, symbol='VNM.VN', side=OrderSide.BUY, order_type=OrderType.LIMIT,
        quantity=1, limit_price=60000, status=OrderStatus.PENDING, filled_quantity=0,
        native_currency=None, fx_rate=1, created_at=datetime.utcnow()-timedelta(minutes=1))
    db_session.add(old); db_session.commit()
    assert process_pending_limit_orders(db_session, account_id=account_id)['filled'] == 0
    assert db_session.query(Trade).count() == db_session.query(Position).count() == 0
    assert db_session.get(Account, account_id).cash_balance == 100000
