"""Native-currency paper wallets. Currency conversion is never implicit."""
from decimal import Decimal
from typing import Literal

from app.data.symbols import DEFAULT_WATCHLIST

AccountCurrency = Literal['USD', 'VND']
STARTING_CASH = {'USD': Decimal('100000'), 'VND': Decimal('1000000000')}
LEGACY_US_SYMBOLS = frozenset(item['symbol'] for item in DEFAULT_WATCHLIST)


def normalize_currency(value: str | None) -> str | None:
    if not value:
        return None
    # Yahoo's GBp quotes are pence, not pounds; never relabel the amount as GBP.
    return 'GBX' if value == 'GBp' else str(value).strip().upper()


def known_currency(symbol: str) -> str | None:
    if symbol.upper().endswith('.VN'):
        return 'VND'
    return 'USD' if symbol.upper() in LEGACY_US_SYMBOLS else None


def quote_currency(db, quote) -> str | None:
    from app.models.models import Symbol
    if quote.currency:
        return normalize_currency(quote.currency)
    instrument = db.query(Symbol).filter(Symbol.symbol == quote.symbol).first()
    return normalize_currency(instrument.currency) if instrument and instrument.currency else known_currency(quote.symbol)


def require_currency(db, account, quote) -> str:
    currency = quote_currency(db, quote)
    if not currency:
        raise ValueError('The quote currency is unavailable. Refresh the investment before trading.')
    if currency != account.currency:
        raise ValueError(f'This investment is priced in {currency}. Select a {currency} portfolio to trade it; this portfolio uses {account.currency}.')
    return currency


def share_step(currency: str) -> Decimal:
    return Decimal('1') if currency == 'VND' else Decimal('0.0001')
