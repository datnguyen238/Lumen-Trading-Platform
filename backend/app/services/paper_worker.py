"""Persistent orders are matched by the API server, independently of any browser."""
import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import OrderStatus
from app.models.models import Order, Position, SavedAsset
from app.services.execution import process_pending_limit_orders
from app.services.pricing import refresh_execution_quote

logger = logging.getLogger(__name__)


class PaperWorker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.wake = asyncio.Event()
        self.symbol_cursor = 0
        self.last_progress_monotonic = time.monotonic()
        self.status = {'enabled': settings.paper_worker_enabled, 'running': False,
                       'last_run': None, 'last_success': None, 'quotes_refreshed': 0,
                       'orders_filled': 0, 'quote_failures': 0}

    def run_once(self):
        self.status['running'] = True
        self.status['last_run'] = datetime.now(timezone.utc).isoformat()
        try:
            with SessionLocal() as db:
                pending = list(db.scalars(select(Order.symbol).where(Order.status == OrderStatus.PENDING).distinct()))
                holdings = list(db.scalars(select(Position.symbol).where(Position.quantity > 0).distinct()))
                saved = list(db.scalars(select(SavedAsset.symbol).distinct()))
                symbols = list(dict.fromkeys(pending + holdings + saved + ['SPY', 'QQQ', 'DIA']))
                # Rotate the batch so a large watchlist cannot starve later symbols.
                count = max(1, settings.paper_worker_symbol_limit)
                start = self.symbol_cursor % max(1, len(symbols))
                selected = (symbols[start:] + symbols[:start])[:count]
                self.symbol_cursor = (start + len(selected)) % max(1, len(symbols))
                refreshed = failures = 0
                for symbol in selected:
                    if self.stop_event.is_set():
                        return
                    self.last_progress_monotonic = time.monotonic()
                    try:
                        refresh_execution_quote(db, symbol)
                        refreshed += 1
                    except Exception:
                        db.rollback()
                        failures += 1
                        logger.warning('Paper worker could not refresh %s', symbol)
                # Process each account separately: every commit releases its wallet lock.
                owners = list(db.scalars(select(Order.account_id).where(Order.status == OrderStatus.PENDING).distinct().order_by(Order.account_id)))
                fills = 0
                for owner in owners:
                    if self.stop_event.is_set():
                        return
                    result = process_pending_limit_orders(db, account_id=owner, limit=500)
                    fills += result['filled']
                self.last_progress_monotonic = time.monotonic()
                self.status.update(last_success=datetime.now(timezone.utc).isoformat(),
                    quotes_refreshed=refreshed, quote_failures=failures, orders_filled=fills)
                logger.info('Paper cycle: quotes=%d filled=%d unavailable=%d', refreshed, fills, failures)
        finally:
            self.status['running'] = False

    async def run(self):
        while not self.stop_event.is_set():
            try:
                await asyncio.to_thread(self.run_once)
            except Exception:
                logger.exception('Paper trading worker cycle failed; it will retry')
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=max(5, settings.paper_worker_interval_seconds))
            except asyncio.TimeoutError:
                pass

    def stop(self):
        self.stop_event.set()
        self.wake.set()
