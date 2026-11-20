"""Resolve company names to listed stock/fund tickers without saving search text."""
from functools import lru_cache
import re
import time

import yfinance as yf

_TICKER = re.compile(r'^[A-Z^][A-Z0-9.^=\-]{0,19}$')
_TYPES = {'EQUITY': 'stock', 'ETF': 'etf'}


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
        items.setdefault(symbol, {'symbol': symbol, 'name': str(name), 'asset_type': asset_type})
    return tuple(items.values())


def search_market_symbols(query: str) -> list[dict]:
    # Bound cache size and lifetime across arbitrary public search terms.
    normalized = ' '.join(query.split()).casefold()
    return [dict(item) for item in _provider_search(normalized, int(time.monotonic() // 300))]
