from types import SimpleNamespace

import pytest

from app.models.models import Symbol
from app.services import symbol_search


@pytest.fixture(autouse=True)
def clear_search_cache():
    symbol_search._provider_search.cache_clear()
    yield
    symbol_search._provider_search.cache_clear()


def test_company_search_returns_canonical_listing_without_saving_query(client, db_session, monkeypatch):
    quotes = [
        {'symbol': 'ANT', 'longname': 'Anthropic PBC', 'quoteType': 'EQUITY'},
        {'symbol': 'ANT', 'shortname': 'Duplicate', 'quoteType': 'EQUITY'},
        {'symbol': 'ANT261120C00100000', 'quoteType': 'OPTION'},
        {'symbol': 'BTC-USD', 'quoteType': 'CRYPTOCURRENCY'},
    ]
    calls = []
    def search(query, **kwargs):
        calls.append(query)
        return SimpleNamespace(response={'quotes': quotes}, quotes=quotes)
    monkeypatch.setattr(symbol_search.yf, 'Search', search)
    for query in ('Anthropic', '  ANTHROPIC  '):
        response = client.get('/symbols/search', params={'q': query})
        assert response.status_code == 200
        assert response.json() == [{'symbol': 'ANT', 'name': 'Anthropic PBC', 'asset_type': 'stock', 'currency': None, 'exchange': None}]
    assert calls == ['anthropic']
    assert db_session.query(Symbol).count() == 0


def test_provider_outage_keeps_local_matches_and_reports_unavailable_search(client, db_session, monkeypatch):
    from app.api import symbols
    db_session.add(Symbol(symbol='AAPL', name='Apple', asset_type='stock'))
    db_session.commit()
    def fail(query):
        raise RuntimeError('provider internals must stay private')
    monkeypatch.setattr(symbols, 'search_market_symbols', fail)
    assert client.get('/symbols/search', params={'q': 'Apple'}).json()[0]['symbol'] == 'AAPL'
    missing = client.get('/symbols/search', params={'q': 'Unknown company'})
    assert missing.status_code == 503
    assert 'provider internals' not in missing.text


def test_no_matches_is_distinct_from_malformed_provider_response(client, monkeypatch):
    monkeypatch.setattr(symbol_search.yf, 'Search', lambda *args, **kwargs: SimpleNamespace(response={'quotes': []}, quotes=[]))
    response = client.get('/symbols/search', params={'q': 'Unlisted example'})
    assert response.status_code == 200 and response.json() == []
    symbol_search._provider_search.cache_clear()
    monkeypatch.setattr(symbol_search.yf, 'Search', lambda *args, **kwargs: SimpleNamespace(response={}, quotes=[]))
    assert client.get('/symbols/search', params={'q': 'Unlisted example'}).status_code == 503


def test_invalid_company_name_is_not_added_as_a_ticker(client, db_session, monkeypatch):
    from app.api import symbols
    monkeypatch.setattr(symbols.yf, 'Ticker', lambda symbol: SimpleNamespace(history=lambda **kwargs: SimpleNamespace(empty=True)))
    response = client.post('/symbols/add', json={'symbol': 'ANTHROPIC'})
    assert response.status_code == 400
    assert db_session.query(Symbol).count() == 0
    assert client.get('/symbols/search', params={'q': 'x' * 81}).status_code == 422
