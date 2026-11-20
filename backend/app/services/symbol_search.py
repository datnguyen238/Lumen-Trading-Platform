"""Resolve company names to listed stock/fund tickers without saving search text."""
from functools import lru_cache
import re
import time

import yfinance as yf
from app.services.currencies import known_currency, normalize_currency

_TICKER = re.compile(r'^[A-Z^][A-Z0-9.^=\-]{0,19}$')
_TYPES = {'EQUITY': 'stock', 'ETF': 'etf'}
_USD_EXCHANGES = {'NYQ', 'NMS', 'NGM', 'NCM', 'ASE', 'PCX', 'BTS'}
_VIETNAM_NAMES = {'vinamilk': ('VNM.VN', 'Vietnam Dairy Products'),
                  'vnm': ('VNM.VN', 'Vietnam Dairy Products'),
                  'vietnam dairy': ('VNM.VN', 'Vietnam Dairy Products'),
                  'fpt': ('FPT.VN', 'FPT Corporation')}


@lru_cache(maxsize=128)
def _provider_search(query: str, cache_window: int) -> tuple[dict, ...]:
    result = yf.Search(query, max_results=8, news_count=0, lists_count=0,
                       recommended=0, include_cb=False, timeout=8)
    # A provider error must not masquerade as a successful search with no matches.
    response = result.response
    if not isinstance(response, dict) or not isinstance(response.get('quotes'), list):
        raise ValueError('Market search returned an invalid response')
    items = {}
    for quote in result.quotes:
        symbol = str(quote.get('symbol', '')).strip().upper()
        asset_type = _TYPES.get(quote.get('quoteType'))
        if not asset_type or not _TICKER.fullmatch(symbol):
            continue
        name = quote.get('longname') or quote.get('shortname') or symbol
        items.setdefault(symbol, {'symbol': symbol, 'name': str(name), 'asset_type': asset_type,
            'currency': normalize_currency(quote.get('currency')) or known_currency(symbol) or ('USD' if quote.get('exchange') in _USD_EXCHANGES else None),
            'exchange': quote.get('exchDisp') or quote.get('exchange')})
    # Yahoo company search omits some HOSE listings that its chart feed supports.
    # Validate explicit .VN tickers and a few common names against that live feed.
    candidate = _VIETNAM_NAMES.get(query)
    if query.upper().endswith('.VN') and _TICKER.fullmatch(query.upper()):
        candidate = (query.upper(), query.upper())
    if candidate and candidate[0] not in items:
        symbol, name = candidate
        ticker = yf.Ticker(symbol)
        history = ticker.history(period='5d', interval='1d', timeout=8)
        if not history.empty:
            metadata = ticker.get_history_metadata() or {}
            currency = normalize_currency(metadata.get('currency')) or known_currency(symbol)
            if currency == 'VND':
                items[symbol] = {'symbol': symbol, 'name': metadata.get('longName') or metadata.get('shortName') or name,
                    'asset_type': 'stock', 'currency': currency, 'exchange': metadata.get('exchangeName') or 'HOSE'}
    return tuple(items.values())


def search_market_symbols(query: str) -> list[dict]:
    # Bound cache size and lifetime across arbitrary public search terms.
    normalized = ' '.join(query.split()).casefold()
    return [dict(item) for item in _provider_search(normalized, int(time.monotonic() // 300))]
